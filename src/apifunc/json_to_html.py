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