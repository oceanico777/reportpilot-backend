import requests
import os

# Configuration (Matches remote_seed.py logic)
BASE_URL = "https://reportpilot-backend1.onrender.com"
TOKEN = "fake-jwt-token-for-auth"
TOUR_ID = "TOUR-VERIFICACION-001"

def test_close_tour():
    print(f"Testing Tour Closure for {TOUR_ID}...")
    
    # 1. Prepare a dummy signature (1x1 transparent pixel or small PNG)
    # Using a small red dot PNG as dummy signature
    dummy_sig_path = "dummy_signature.png"
    # Create a small dummy image file if it doesn't exist
    from PIL import Image
    img = Image.new('RGB', (100, 30), color = (73, 109, 137))
    img.save(dummy_sig_path)

    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        with open(dummy_sig_path, "rb") as f:
            files = {"signature": (dummy_sig_path, f, "image/png")}
            resp = requests.post(f"{BASE_URL}/tours/{TOUR_ID}/close", headers=headers, files=files)
            
        if resp.status_code == 200:
            print("SUCCESS: Tour closed. PDF generated.")
            print(f"Result: {resp.json()}")
        else:
            print(f"FAILED: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        if os.path.exists(dummy_sig_path):
            os.remove(dummy_sig_path)

if __name__ == "__main__":
    test_close_tour()
