import weasyprint


def html_to_pdf(html_content: str) -> bytes:
    """
    Konwersja HTML do PDF
    """
    html = weasyprint.HTML(string=html_content)
    # Check if any additional parameters are needed for write_pdf()
    return html.write_pdf()