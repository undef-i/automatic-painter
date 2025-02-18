from collections import deque
import time

class TokenManager:
    def __init__(self):
        self.active_tokens = deque(maxlen=20)
        
    def add_token(self, token_str, color):
        self.active_tokens.append({
            'token': token_str,
            'color': color,
            'expiry': time.time() + 30000,
            'remaining_uses': 10,
            'last_used': 0
        })
    
    def get_valid_token(self, target_color):
        now = time.time()
        valid_tokens = [
            t for t in self.active_tokens
            if t['remaining_uses'] > 0
            and t['expiry'] > now
            and t['color'] == target_color
        ]
        if valid_tokens:
            valid_tokens.sort(key=lambda x: x['remaining_uses'], reverse=True)
            return valid_tokens[0]
        return None
    
    def mark_used(self, token_obj):
        assert isinstance(token_obj, dict), "Must pass token dictionary object"
        token_obj['remaining_uses'] -= 1
        token_obj['last_used'] = time.time()
    
    def get_token_by_str(self, token_str):
        return next(
            (t for t in self.active_tokens if t['token'] == token_str),
            None
        ) 