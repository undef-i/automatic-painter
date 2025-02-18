import argparse
from client import PainterClient
from processor import ColorProcessor

def main():
    parser = argparse.ArgumentParser(description='Pixel Art Drawing Tool')
    parser.add_argument('--image', '-i', type=str, required=True,
                      help='Path to the image to draw')
    parser.add_argument('--x', '-x', type=int, required=True,
                      help='Starting X coordinate')
    parser.add_argument('--y', '-y', type=int, required=True,
                      help='Starting Y coordinate')
    parser.add_argument('--threshold', '-t', type=int, required=True,
                      help='Color similarity threshold')
    parser.add_argument('--skip-scan', '-s', action='store_true',
                      help='Skip canvas scanning')
    parser.add_argument('--url', '-u', type=str, required=True,
                      help='Server URL')
    parser.add_argument('--private-keys', '-p', type=str, default='private_keys',
                      help='Path to private keys file (default: private_keys)')

    args = parser.parse_args()
    
    client = PainterClient(base_url=args.url)
    
    processor = ColorProcessor(
        args.image, 
        args.x, 
        args.y, 
        args.threshold,
        skip_scan=args.skip_scan,
        private_keys_path=args.private_keys
    )
    
    width, height = processor.image.size
    processor.progress.update_file_info(args.image, args.x, args.y, width, height)
    
    try:
        processor.process_colors(client)
    except KeyboardInterrupt:
        print("Program interrupted, exiting...")
        processor.progress.stop()
        exit(0)

if __name__ == "__main__":
    main() 