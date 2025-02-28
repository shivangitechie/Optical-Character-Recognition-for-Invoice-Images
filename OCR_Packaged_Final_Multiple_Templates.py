#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Importing required libraries
from datetime import datetime
import mysql.connector
import cv2  # For image processing
import os
import numpy as np
import pytesseract  # For OCR
from pytesseract import Output
import re  # For template matching
import pandas as pd

# Connect to MySQL Database
conn = mysql.connector.connect(
    host="localhost",  # Change if your MySQL is on a different host
    user="root",       # Your MySQL username
    password="password",  # Your MySQL password
    database="invoices_db"
)
cursor = conn.cursor()

def store_invoice_data(extracted_data):
    """Stores invoice data in MySQL, avoiding duplicates."""
    try:
        # Convert date format from 'DD.MM.YYYY' to 'YYYY-MM-DD'
        if extracted_data["Invoice Date"]:
            try:
                formatted_date = datetime.strptime(extracted_data["Invoice Date"], "%d.%m.%Y").strftime("%Y-%m-%d")
            except ValueError:
                print("Date format error! Using NULL instead.")
                formatted_date = None
        else:
            formatted_date = None
            
        query = """
            INSERT INTO invoices (company, invoice_number, invoice_date, total_amount) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                invoice_date = VALUES(invoice_date), 
                total_amount = VALUES(total_amount)
            """

        values = (
            extracted_data["Company"],
            extracted_data["Invoice Number"],
            formatted_date,  # ✅ Use the formatted date
            extracted_data["Total Amount"]
        )

        cursor.execute(query, values)
        conn.commit()
        print("Data Inserted Successfully!")
    except mysql.connector.IntegrityError:
        print("Duplicate Entry! Invoice already exists.")

# Set the pytesseract path

# Main code for Invoice OCR
def OCR_INVOICE(image_path):
    # Ask the user to enter the name of the company/organization:
    company_name = input("Enter The Name of the Company (Flipkart, Myntra, Amazon): ").capitalize()
    companies = ['Flipkart', 'Amazon', 'Myntra']
    
    # Check if the company template exists
    if company_name not in companies:
        print("Template Not Found")
        return
    
    # IMAGE PREPROCESSING STEPS
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Grayscale
    noiseless = cv2.GaussianBlur(gray, (5, 5), 0)  # Gaussian Blurring
    thresh = cv2.threshold(noiseless, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]  # Thresholding

    # Erosion and dilation
    kernel = np.ones((2, 2), np.uint8)
    processed_image = cv2.erode(thresh, kernel, iterations=1)

    # Save preprocessed image
    cv2.imwrite('preprocessed-invoice-sample-image.jpg', processed_image)

    # OCR Processing
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    d = pytesseract.image_to_data(image_rgb, output_type=Output.DICT)

    # Define patterns for extracting key details
    date_patterns = [r'\d{2}-\d{2}-\d{4}', r'\d{2}.\d{2}.\d{4}', r'\d{2}/\d{2}/\d{4}']
    
    invoice_patterns = [
        r'\b\d{3}-\d{7}-\d{7}\b',  # 404-1234567-8901234 (Order Number)
        r'\b[A-Z]{2}-IN-\d{6,10}\b',  # DE-IN-1234567 (Tax Invoice)
        r'\bAMZ\d{6,10}\b',  # AMZ12345678 (Amazon Business)
        r'\bGB\d{9,10}\b',  # GB123456789 (VAT Invoice)
        r'\bIN-\d{6,10}\b',  # IN-123456789 (India Invoice)
        r'\b[A-Z]{2}-AEU-INV-[A-Z]{2}-\d{4}-\d{5}\b',
        r'\b[A-Z]{3}\d{6}\b'
    ]

    amount_patterns = [
        r'[$€£₹]\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',  # Matches: $1,234.56 | € 1.234,56 | £1234.56 | ₹ 1,23,456.78
        r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[$€£₹]',  # Matches: 1,234.56$ | 1.234,56€ | 1234.56£ | 1,23,456.78₹
    ]


    # Dictionary to store extracted details
    extracted_data = {
        "Company": company_name,
        "Invoice Number": None,
        "Invoice Date": None,
        "Total Amount": None
    }

    n_boxes = len(d['text'])
    
    for i in range(n_boxes):
        text = d['text'][i].strip()
        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]

        if text:
            # Match Invoice Number
            for pattern in invoice_patterns:
                if re.fullmatch(pattern, text):
                    extracted_data["Invoice Number"] = text
                    cv2.rectangle(image_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(image_rgb, "Invoice No.", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Match Invoice Date
            for pattern in date_patterns:
                if re.fullmatch(pattern, text):
                    extracted_data["Invoice Date"] = text
                    cv2.rectangle(image_rgb, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.putText(image_rgb, "Date", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            # Match Total Amount
            for pattern in amount_patterns:
                if re.fullmatch(pattern, text):
                    extracted_data["Total Amount"] = text
                    cv2.rectangle(image_rgb, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(image_rgb, "Total Amount", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # Display the processed image
    cv2.imshow('Extracted Invoice Data', image_rgb)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("\nExtracted Data:")
    print(extracted_data)
    
    if extracted_data["Invoice Number"]:
        store_invoice_data(extracted_data)
    else:
        print("Invoice Number not detected! Skipping entry.")

    return extracted_data

# Test with an invoice image
# Amazon
invoice_data = OCR_INVOICE("amazon_us")
invoice_data = OCR_INVOICE("amazon_uk")

conn.close()


# In[ ]:




