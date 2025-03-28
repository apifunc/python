from typing import Dict

from jinja2 import Template


# Przykładowe komponenty transformacji
def json_to_html(json_data: Dict) -> str:
    """
    Transformacja JSON do HTML
    """
    html_template = """
    <html>
    <body>
        <h1>Raport</h1>
        <table>
            {% for key, value in data.items() %}
            <tr>
                <td>{{ key }}</td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    template = Template(html_template)
    return template.render(data=json_data)



# Define the pipeline components as functions
def json_to_html2(json_data):
    """Convert JSON data to HTML"""
    try:
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # Create a simple HTML representation
        html = f"""
        <html>
        <head>
            <title>{data.get('title', 'Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                .info {{ color: #7f8c8d; margin-bottom: 20px; }}
                .content {{ line-height: 1.6; }}
            </style>
        </head>
        <body>
            <h1>{data.get('title', 'Report')}</h1>
            <div class="info">
                <p>Author: {data.get('author', 'Unknown')}</p>
                <p>Date: {data.get('date', 'N/A')}</p>
            </div>
            <div class="content">
                <p>{data.get('content', '')}</p>
            </div>
        </body>
        </html>
        """

        return html
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {e}")
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"
