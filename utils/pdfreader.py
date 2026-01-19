from pypdf import PdfReader
reader = PdfReader("yolo_test/input/bottleneck.pdf")
pages = len(reader.pages)
pages = reader.pages

page_schema = []

for page in pages:
    text = page.extract_text()
    page_schema.append(text)

print(page_schema)