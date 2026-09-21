from pdf2image import convert_from_path
import pytesseract


def extract_text_from_page_with_ocr(pdf_path, page_number):
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
    return pytesseract.image_to_string(images[0])