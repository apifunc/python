import weasyprint


def html_to_pdf(html_content: str) -> bytes:
    """
    Konwersja HTML do PDF
    """
    html = weasyprint.HTML(string=html_content)
    # Check if any additional parameters are needed for write_pdf()
    return html.write_pdf()


def html_to_pdf2(html_content):
    """Convert HTML to PDF using WeasyPrint"""
    try:
        # Import WeasyPrint here to avoid dependency issues
        from weasyprint import HTML
        import io

        # Convert HTML to PDF
        pdf_buffer = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)

        # Return PDF as base64 encoded string for gRPC transport
        pdf_data = pdf_buffer.getvalue()
        return base64.b64encode(pdf_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {e}")
        raise