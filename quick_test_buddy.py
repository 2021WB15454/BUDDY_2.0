import requests, os
from dynamic_config import get_host, get_port
import json

def quick_test():
    # Test greeting
    base = f"http://{get_host()}:{get_port()}"
    response = requests.post(f'{base}/chat', 
                           json={'message': 'Hello BUDDY!', 'user_id': 'test_user'})
    print("Greeting test:", response.json().get('response') if response.status_code == 200 else "Failed")
    
    # Test how are you
    response = requests.post(f'{base}/chat', 
                           json={'message': 'How are you?', 'user_id': 'test_user'})
    print("How are you test:", response.json().get('response') if response.status_code == 200 else "Failed")
    
    # Test weather
    response = requests.post(f'{base}/chat', 
                           json={'message': 'What is the weather in Trichy?', 'user_id': 'test_user'})
    print("Weather test:", response.json().get('response') if response.status_code == 200 else "Failed")

if __name__ == "__main__":
    quick_test()
