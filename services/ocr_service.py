"""
OCR Service
Extract text from images
"""


from PIL import Image

import pytesseract





def extract_text(image_path):


    try:


        image = Image.open(

            image_path

        )


        text = pytesseract.image_to_string(

            image

        )


        return text.strip()



    except Exception as e:


        return f"OCR Error: {str(e)}"








def extract_table_text(image_path):


    text = extract_text(

        image_path

    )


    return """

Extracted table text:


{}

""".format(text)