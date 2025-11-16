from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message
import re
import os

class UnifiedTextProcessor(Component):
    display_name = "Text Processor"
    description = "Handles text/image/URL inputs"
    
    inputs = [
        MessageTextInput(
            name="user_input",
            display_name="User Input",
            info="Text, screenshot, or URL"
        )
    ]
    
    outputs = [
        Output(display_name="Processed Text", name="output", method="process_input")
    ]
    
    def process_input(self) -> Message:
        user_input = self.user_input
        processed_text = ""
        
        print(f"DEBUG - Input received: {user_input}")
        print(f"DEBUG - Input type: {type(user_input)}")
        
        # Check if user_input is a Message object with files
        if hasattr(user_input, 'files') and user_input.files:
            print("DEBUG - Files attribute found")
            try:
                import pytesseract
                from PIL import Image
                
                file_path = user_input.files[0]
                print(f"DEBUG - File path: {file_path}")
                
                # Configure Tesseract
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                
                # Open and process image
                image = Image.open(file_path)
                image = image.convert('L')  # Grayscale
                
                # OCR
                custom_config = r'--oem 3 --psm 6 -l eng'
                processed_text = pytesseract.image_to_string(image, config=custom_config)
                
                print(f"DEBUG - OCR extracted: {processed_text[:200]}")
                
            except Exception as e:
                print(f"DEBUG - OCR Error: {str(e)}")
                processed_text = f"Error: {str(e)}"
        
        # Check if user_input has a text attribute
        elif hasattr(user_input, 'text'):
            text_content = user_input.text
            print(f"DEBUG - Text from message: {text_content[:100] if text_content else 'EMPTY'}")
            
            # If text is empty but there might be a file reference
            if not text_content or text_content.strip() == "":
                # Check if there's a file reference in the message data
                if hasattr(user_input, 'data') and user_input.data:
                    print(f"DEBUG - Message data: {user_input.data}")
                    
                    # Look for file path in data
                    if 'file_path' in user_input.data:
                        try:
                            import pytesseract
                            from PIL import Image
                            
                            file_path = user_input.data['file_path']
                            print(f"DEBUG - Found file path in data: {file_path}")
                            
                            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                            
                            image = Image.open(file_path)
                            image = image.convert('L')
                            custom_config = r'--oem 3 --psm 6 -l eng'
                            processed_text = pytesseract.image_to_string(image, config=custom_config)
                            
                            print(f"DEBUG - OCR from data path: {processed_text[:200]}")
                        except Exception as e:
                            print(f"DEBUG - Error processing file from data: {str(e)}")
                            processed_text = ""
                else:
                    processed_text = ""
            else:
                # Handle URL
                if text_content.startswith('http'):
                    try:
                        import requests
                        from bs4 import BeautifulSoup
                        
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        response = requests.get(text_content, headers=headers, timeout=10)
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        processed_text = soup.get_text()
                        processed_text = ' '.join(processed_text.split())[:3000]
                    except Exception as e:
                        processed_text = text_content
                else:
                    # Plain text
                    processed_text = text_content
        
        # Fallback: treat as string
        else:
            user_input_str = str(user_input)
            print(f"DEBUG - String input: {user_input_str[:100]}")
            
            if user_input_str.startswith('http'):
                # URL handling
                try:
                    import requests
                    from bs4 import BeautifulSoup
                    
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(user_input_str, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    processed_text = soup.get_text()
                    processed_text = ' '.join(processed_text.split())[:3000]
                except:
                    processed_text = user_input_str
            else:
                processed_text = user_input_str
        
        # Clean text
        if processed_text:
            processed_text = re.sub(r'\s+', ' ', processed_text)
            processed_text = processed_text[:3000].strip()
        
        print(f"DEBUG - Final output length: {len(processed_text)}")
        print(f"DEBUG - Final output preview: {processed_text[:200]}")
        
        return Message(text=processed_text if processed_text else "No text could be extracted from input")
