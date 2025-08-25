import requests
import json

def quick_test():
    # Test greeting
    response = requests.post('http://localhost:8082/chat', 
                           json={'message': 'Hello BUDDY!', 'user_id': 'test_user'})
    print("Greeting test:", response.json().get('response') if response.status_code == 200 else "Failed")
    
    # Test how are you
    response = requests.post('http://localhost:8082/chat', 
                           json={'message': 'How are you?', 'user_id': 'test_user'})
    print("How are you test:", response.json().get('response') if response.status_code == 200 else "Failed")
    
    # Test weather
    response = requests.post('http://localhost:8082/chat', 
                           json={'message': 'What is the weather in Trichy?', 'user_id': 'test_user'})
    print("Weather test:", response.json().get('response') if response.status_code == 200 else "Failed")

if __name__ == "__main__":
    quick_test()
