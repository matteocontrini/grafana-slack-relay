import logging
import os
import sys
from datetime import datetime

import requests
from flask import Flask, request

from utils import json_serialize

app = Flask(__name__)

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z',
    level=logging.INFO
)


@app.route('/webhook', methods=['POST'])
def grafana_webhook():
    data = request.json

    logging.info(f'Received webhook: {json_serialize(data)}')

    attachments = [format_slack_attachment(alert) for alert in data['alerts']]
    message = {
        'attachments': attachments
    }

    logging.info(f'Sending slack message: {json_serialize(message)}')

    response = requests.post(SLACK_WEBHOOK_URL, json=message)

    if response.text != 'ok':
        logging.error(f'Error sending slack message: {response.text}')
        return response.text, 503

    return 'ok', 200


def format_slack_attachment(alert: dict) -> dict:
    title = build_title(alert)
    text = build_text(alert)
    fallback = f'{title}\n{text}'
    actions = build_actions(alert)

    return {
        'color': '#D63232' if alert['status'] == 'firing' else '#36A64F',
        'title': title,
        'title_link': alert['panelURL'],
        'footer': 'Grafana',
        'footer_icon': 'https://grafana.com/static/assets/img/fav32.png',
        'ts': datetime.fromisoformat(alert['startsAt']).timestamp(),
        'text': text,
        'fallback': fallback,
        'fields': build_attachment_fields(alert),
        'mkrdwn_in': ['text'],
        'image_url': alert.get('imageURL'),
        'actions': actions
    }


def build_title(alert):
    alert_name = alert['labels']['alertname']
    rule_name = alert['labels'].get('rulename')
    if rule_name:
        alert_name += f': {rule_name}'
    icon = '🚨' if alert['status'] == 'firing' else '✅'
    text = f'{icon} {alert_name}'
    return text


def build_text(alert):
    text = ''
    summary = alert['annotations'].get('summary')
    if summary:
        text = f'{summary}'
    description = alert['annotations'].get('description')
    if description:
        text += f'\n{description}'
    return text


def build_attachment_fields(alert):
    fields = []
    if alert['values']:  # exclude no data or error alerts
        for key, value in alert['annotations'].items():
            if key == 'summary' or key == 'description':
                continue
            try:
                float_value = float(value)
            except ValueError:
                float_value = None
            fields.append({
                'title': key,
                'value': f'{float_value:.1f}' if float_value is not None else value,
                'short': True
            })
    if 'Error' in alert['annotations']:
        fields.append({
            'title': 'Error',
            'value': alert['annotations']['Error'],
            'short': False
        })

    return fields


def build_actions(alert):
    actions = [
        {
            'type': 'button',
            'text': '🔕 Silence',
            'url': alert['silenceURL']
        },
        {
            'type': 'button',
            'text': 'ℹ️ Go to rule',
            'url': alert['generatorURL']
        }
    ]

    if 'dashboardURL' in alert:
        actions.append({
            'type': 'button',
            'text': '📊 Dashboard',
            'url': alert['dashboardURL']
        })
    if 'panelURL' in alert:
        actions.append({
            'type': 'button',
            'text': '📈 Panel',
            'url': alert['panelURL']
        })
    return actions


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error('Unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_unhandled_exception

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(port=port)
