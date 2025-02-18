# Automatic Painter


Automated drawing tool for PKU HPCGame 2nd.

## Usage

```bash
python src/main.py -i <image> -x <x_coord> -y <y_coord> -t <threshold> -u <url> [-s] [-p private_keys_data_path]
```

Required:
- `-i`: Image path
- `-x`: X coordinate
- `-y`: Y coordinate
- `-t`: Color threshold
- `-u`: Server URL

Optional:
- `-s`: Skip canvas scan
- `-p`: Private keys data path 