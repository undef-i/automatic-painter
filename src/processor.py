import os
from collections import defaultdict
from PIL import Image
from rich.console import Console
from token_manager import TokenManager
from progress import ProgressManager
from utils import color_distance, read_private_key
import subprocess
import logging

class ColorProcessor:
    def __init__(self, image_path, offset_x, offset_y, color_threshold=30, skip_scan=False, private_keys_path='private_keys'):
        self.image = Image.open(image_path).convert('RGBA')
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.color_threshold = color_threshold
        self.skip_scan = skip_scan
        self.private_keys_path = private_keys_path
        self.temp_console = Console()
        
        self.token_manager = TokenManager()
        self.pixel_cache = self.load_pixel_cache()
        
        self.painted = {
            coord: data['color']
            for coord, data in self.pixel_cache.items()
            if data['source'] == 'paint'
        }
        
        if not skip_scan:
            self.scan_target_area(client)
        
        color_data, skipped_pixels = self.analyze_colors()
        
        self.total_colors = len(color_data)
        raw_pixels = sum(len(coords) for _, coords in color_data)
        self.total_pixels = raw_pixels
        self.total_tasks = raw_pixels // 10
        if raw_pixels % 10 > 0:
            self.total_tasks += 1
            
        self.temp_console.print(f"Found {skipped_pixels} pixels matching target colors, processing {raw_pixels} pixels")
        
        self.total_colors = len(color_data)
        raw_pixels = sum(len(coords) for _, coords in color_data)
        self.total_pixels = raw_pixels
        self.total_tasks = sum((len(coords) + 9) // 10 for _, coords in color_data)
        self.completed_pixels = 0
        
        self.progress = ProgressManager(self.total_colors, self.total_pixels, self.total_tasks)
        self.color_queue = color_data

    def load_pixel_cache(self):
        pixel_cache = {}
        cache_file = "pixel.cache"
        
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 6:
                        try:
                            x, y = int(parts[0]), int(parts[1])
                            r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                            source = parts[5]
                            new_color = (r, g, b)
                            best_color = new_color
                            min_distance = float('inf')
                            
                            for existing_data in pixel_cache.values():
                                existing_color = existing_data['color']
                                dist = color_distance(existing_color, new_color)
                                if dist < self.color_threshold and dist < min_distance:
                                    min_distance = dist
                                    best_color = existing_color
                            
                            pixel_cache[(x, y)] = {
                                'color': best_color,
                                'source': source
                            }
                        except ValueError:
                            continue
        return pixel_cache

    def save_pixel_data(self, x, y, rgb, source):
        cache_file = "pixel.cache"
        with open(cache_file, "a") as f:
            f.write(f"{x},{y},{rgb[0]},{rgb[1]},{rgb[2]},{source}\n")
        self.pixel_cache[(x, y)] = {
            'color': rgb,
            'source': source
        }

    def scan_target_area(self, client):
        self.temp_console.print("Starting to scan target area colors...")
        width, height = self.image.size
        
        total_pixels = width * height
        scanned = 0
        skipped = 0
        
        scan_coords = []
        for x in range(width):
            for y in range(height):
                board_x = x + self.offset_x
                board_y = y + self.offset_y
                
                r, g, b, a = self.image.getpixel((x, y))
                if a < 255:
                    skipped += 1
                    continue
                    
                if (board_x, board_y) in self.pixel_cache:
                    skipped += 1
                    continue
                    
                scan_coords.append((board_x, board_y))

        total_to_scan = len(scan_coords)
        if total_to_scan == 0:
            self.temp_console.print("All pixels are cached, no scanning needed!", style="green")
            return

        self.temp_console.print(f"Need to scan {total_to_scan} pixels, skipped {skipped} cached/white pixels", style="yellow")
        
        for board_x, board_y in scan_coords:
            try:
                pixel_info = client.pixel_get(board_x, board_y)
                r = int(pixel_info.get('r', 0))
                g = int(pixel_info.get('g', 0))
                b = int(pixel_info.get('b', 0))
                self.save_pixel_data(board_x, board_y, (r, g, b), 'scan')
                scanned += 1
                
                if scanned % 100 == 0:
                    percentage = (scanned / total_to_scan) * 100
                    self.temp_console.print(f"Scan progress: {percentage:.1f}% ({scanned}/{total_to_scan})")
                    
            except Exception as e:
                self.temp_console.print(f"Failed to scan position ({board_x, board_y}): {str(e)}", style="red")
                continue
        
        self.temp_console.print(f"Scan complete! Scanned {scanned} pixels, skipped {skipped} pixels", style="green") 

    def get_pixel_color(self, x, y):
        board_x = x + self.offset_x
        board_y = y + self.offset_y
        
        pixel_data = self.pixel_cache.get((board_x, board_y))
        return pixel_data['color'] if pixel_data else None

    def analyze_colors(self):
        color_map = defaultdict(list)
        width, height = self.image.size
        skipped_pixels = 0
        
        for x in range(width):
            for y in range(height):
                r, g, b, a = self.image.getpixel((x, y))
                
                if a < 255:
                    continue
                
                board_x = x + self.offset_x
                board_y = y + self.offset_y
                target_color = (r, g, b)
                
                cached_data = self.pixel_cache.get((board_x, board_y))
                if cached_data:
                    cached_color = cached_data['color']
                    if color_distance(cached_color, target_color) < self.color_threshold:
                        skipped_pixels += 1
                        continue
                
                color_map[target_color].append((x, y))
        
        if skipped_pixels > 0:
            self.temp_console.print(
                f"Skipped {skipped_pixels} pixels with similar colors from cache (threshold: {self.color_threshold})"
            )
        
        merged_map = self.merge_similar_colors(color_map)
        
        def color_darkness(color_data):
            color = color_data[0]
            return sum(color)
        
        return sorted(merged_map.items(), key=color_darkness), skipped_pixels

    def merge_similar_colors(self, color_map):
        merged_colors = {}
        merged_map = defaultdict(list)
        
        colors = sorted(color_map.items(), key=lambda x: -len(x[1]))
        
        for color, pixels in colors:
            found = False
            for base_color in merged_colors:
                if color_distance(color, base_color) < self.color_threshold:
                    merged_map[base_color].extend(pixels)
                    merged_colors[base_color].append(color)
                    found = True
                    break
            
            if not found:
                merged_colors[color] = [color]
                merged_map[color] = pixels
        
        for base_color, similar_colors in merged_colors.items():
            if len(similar_colors) > 1:
                pixels_count = len(merged_map[base_color])
                self.temp_console.print(
                    f"Merged color group: {base_color} <- {similar_colors[1:]} ({pixels_count} pixels)"
                )
        
        return merged_map

    def save_merged_image(self, output_path="demo.png"):
        merged_image = self.image.copy()
        pixels = merged_image.load()
        width, height = merged_image.size
        
        color_mapping = {}
        
        for x in range(width):
            for y in range(height):
                r, g, b, a = merged_image.getpixel((x, y))
                if (r, g, b, a) == (255, 255, 255, 255) or a < 255:
                    continue
                
                board_x = x + self.offset_x
                board_y = y + self.offset_y
                target_color = (r, g, b)
                
                if target_color in color_mapping:
                    final_color = color_mapping[target_color]
                else:
                    min_distance = float('inf')
                    final_color = target_color
                    
                    cached_data = self.pixel_cache.get((board_x, board_y))
                    if cached_data:
                        cached_color = cached_data['color']
                        dist = color_distance(cached_color, target_color)
                        if dist < self.color_threshold:
                            final_color = cached_color
                    
                    color_mapping[target_color] = final_color
                
                pixels[x, y] = final_color + (255,)
        
        merged_image.save(output_path)
        self.temp_console.print(
            f"Preview image saved to {output_path} (color threshold: {self.color_threshold})", 
            style="green"
        )

    def process_colors(self, client):
        self.save_merged_image("demo.png")
        
        self.progress.start()
        try:
            for i, color_info in enumerate(self.color_queue, 1):
                self.progress.log(f"Processing color {i}/{self.total_colors}")
                target_rgb, img_coords = color_info
                completed = self.process_single_color(target_rgb, img_coords, client)
                self.completed_pixels += completed
                self.progress.advance_total(self.completed_pixels)
        finally:
            self.progress.stop()

    def process_single_color(self, target_rgb, img_coords, client):
        total_pixels = len(img_coords)
        color_square = f"[rgb({target_rgb[0]},{target_rgb[1]},{target_rgb[2]})]■[/]"
        description = f"{color_square} RGB{target_rgb}"
        completed_count = 0

        if hasattr(self.progress, 'color_task') and self.progress.color_task is not None:
            try:
                task = self.progress.color_progress.tasks[self.progress.color_task]
                if task and task.description and "100%" in str(task.percentage):
                    self.progress.log(f"Completed: {task.description}", "success")
            except (IndexError, AttributeError):
                pass
            self.progress.color_progress.remove_task(self.progress.color_task)
        
        self.progress.init_color_progress(total_pixels, description)
        self.progress.log(f"Starting: {description}", "info")
        
        batch_size = 50
        remaining_coords = img_coords.copy()
        
        while remaining_coords and completed_count < total_pixels:
            valid_token = self.token_manager.get_valid_token(target_rgb)
            
            if valid_token:
                self.progress.log(f"Using existing token: {valid_token['token']} ({valid_token['remaining_uses']} uses remaining)", "success")
                current_batch = remaining_coords[:batch_size]
                success_count = self.paint_pixels(target_rgb, current_batch, valid_token['token'], client)
                
                if success_count > 0:
                    remaining_coords = remaining_coords[success_count:]
                    completed_count = min(completed_count + success_count, total_pixels)
                    self.progress.update_color(advance=success_count)
            
            else:
                job = self.get_job_with_retry(client)
                if not job:
                    self.progress.log("Failed to get job", "error")
                    continue
                
                try:
                    proofs, jobid = self.process_job(job, target_rgb)
                    token_str = self.submit_proofs(client, proofs, jobid, target_rgb)
                    if not token_str:
                        self.progress.log("Failed to submit proofs", "error")
                        continue
                        
                except Exception as e:
                    self.progress.log(f"Failed to process job: {str(e)}", "error")
                    continue
            
            if not remaining_coords or completed_count >= total_pixels:
                break
                
        return completed_count

    def get_job_with_retry(self, client, max_retries=None):
        attempt = 1
        while True:
            try:
                job = client.job_get()
                self.progress.log(f"Got job {job['jobid'][:8]}...", "info")
                return job
            except Exception as e:
                self.progress.log(f"Failed to get job (attempt {attempt}): {str(e)}", "warning")
                attempt += 1
                continue

    def process_job(self, job, target_rgb):
        if not all(0 <= c <= 255 for c in target_rgb):
            raise ValueError(f"Invalid RGB value: {target_rgb}")
        
        components = {
            'r': f"{target_rgb[0]:02x}",
            'g': f"{target_rgb[1]:02x}",
            'b': f"{target_rgb[2]:02x}"
        }
        
        proofs = {}
        color_names = {
            'r': 'RED',
            'g': 'GREEN',
            'b': 'BLUE'
        }
        
        for i, color in enumerate(['r', 'g', 'b']):
            full_prefix = components[color] + job[color]
            self.progress.log(f"Generating {color_names[color]} proof...", "info")
            proofs[color] = self.safe_vanity(full_prefix)
            
        self.progress.log("All proofs generated successfully", "success")
        return proofs, job['jobid']
    
    def safe_vanity(self, prefix, max_attempts=3):
        for attempt in range(1, max_attempts+1):
            try:
                private_key = read_private_key(prefix, self.private_keys_path)
                if not (private_key is None):
                    return {
                        'private_key': private_key,
                        'address': None
                    }
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as e:
                logging.error(f"Attempt {attempt} failed: {str(e)}")
            
        
        raise RuntimeError(f"Could not generate valid proof for prefix {prefix}")
    
    def submit_proofs(self, client, proofs, jobid, target_rgb):
        try:
            response = client.job_submit(
                r=proofs['r']['private_key'],
                g=proofs['g']['private_key'],
                b=proofs['b']['private_key'],
                jobid=jobid
            )
            token_str = response['token']
            self.progress.log(f"Got token: {token_str}", "success")
            
            self.token_manager.add_token(token_str, target_rgb)
            
            return token_str
        except Exception as e:
            self.progress.log(f"Submission failed: {str(e)}", "error")
            return None
    
    def paint_pixels(self, target_rgb, img_coords, token_str, client):
        token_obj = self.token_manager.get_token_by_str(token_str)
        if not token_obj:
            self.progress.log(f"Invalid token: {token_str}", "error")
            return 0
        
        success_count = 0
        batch_size = min(50, len(img_coords))
        current_task_pixels = 0
        
        for i in range(batch_size):
            if token_obj['remaining_uses'] <= 0:
                self.progress.log("Token usage count exhausted", "warning")
                break
            
            img_x, img_y = img_coords[i]
            board_x = img_x + self.offset_x
            board_y = img_y + self.offset_y
            
            try:
                client.pixel_set(
                    x=board_x,
                    y=board_y,
                    token=token_str
                )
                
                self.painted[(board_x, board_y)] = target_rgb
                self.record_painted_pixel(board_x, board_y, target_rgb)
                success_count += 1
                current_task_pixels += 1
                self.progress.update_color()
                
                if current_task_pixels == 10:
                    self.progress.advance_task()
                    current_task_pixels = 0
                
                self.token_manager.mark_used(token_obj)
                
            except Exception as e:
                self.progress.log(f"Failed to paint ({board_x}, {board_y}): {str(e)}", "error")
                self.update_pixel_cache(board_x, board_y, client)
        
        if current_task_pixels > 0:
            self.progress.advance_task()
        
        return success_count

    def record_painted_pixel(self, x, y, rgb):
        self.save_pixel_data(x, y, rgb, 'paint')

    def update_pixel_cache(self, x, y, client):
        try:
            pixel_info = client.pixel_get(x, y)
            actual_rgb = (
                int(pixel_info.get('r', 0)),
                int(pixel_info.get('g', 0)),
                int(pixel_info.get('b', 0))
            )
            self.save_pixel_data(x, y, actual_rgb, 'scan')
        except Exception as e:
            self.progress.log(f"Failed to update cache: {str(e)}", "error") 