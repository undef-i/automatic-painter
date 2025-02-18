import os

def read_private_key(prefix, private_keys_path):
    if not os.path.exists(private_keys_path):
        raise FileNotFoundError(f"Required private key file not found: {private_keys_path}")
        
    prefix = "0x"+prefix.lower()
    
    try:
        index = int(prefix, 16)
        
        with open(private_keys_path, 'rb') as f:
            f.seek(index * 32)
            private_key_bytes = f.read(32)
            if len(private_key_bytes) != 32:
                raise ValueError("Invalid private key data")
        return private_key_bytes.hex()
    except (ValueError, IOError) as e:
        raise RuntimeError(f"Failed to read private key: {str(e)}")

def color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5 