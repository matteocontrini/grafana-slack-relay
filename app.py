import json
import logging
import os
from datetime import datetime

import requests
from flask import Flask, request

app = Flask(__name__)

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

logging.basicConfig(format='%(asctime)s %(levelname)s [%(name)s] %(message)s', level=logging.INFO)


@app.route('/webhook', methods=['POST'])
def grafana_webhook():
    data = request.json

    logging.info(f'Received webhook: {data}')

    for alert in data['alerts']:
        slack_message = format_slack_message(alert)
        logging.info(f'Sending slack message: {slack_message}')
        print(json.dumps(slack_message, ensure_ascii=False))
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_message)

        if response.text != 'ok':
            logging.error(f'Error sending slack message: {response.text}')
            return response.text, 503

    return 'ok', 200


def format_slack_message(alert: dict) -> dict:
    blocks = [
        build_summary_block(alert),
        build_fields_block(alert),
        build_actions_block(alert),
        build_image_block(alert),
        build_footer(alert)
    ]

    # Remove none from blocks
    blocks = [x for x in blocks if x is not None]

    # TODO: test "no data" and "error"

    return {
        'text': build_notification_text(alert),
        'blocks': blocks,
        # 'attachments': [
        #     {
        #         'color': '#D63232' if alert['status'] == 'firing' else '#36A64F',
        #         'blocks': blocks
        #     }
        # ]
    }


def build_notification_text(alert):
    alert_name = alert['labels']['alertname']
    icon = '🚨' if alert['status'] == 'firing' else '✅'
    text = f'{icon} *{alert_name}*'

    summary = alert['annotations'].get('summary')
    if summary:
        text += f'\n{summary}'
    description = alert['annotations'].get('description')
    if description:
        text += f'\n{description}'

    return text


def build_summary_block(alert):
    panel_url = alert['panelURL']
    alert_name = alert['labels']['alertname']
    icon = '🚨' if alert['status'] == 'firing' else '✅'
    text = f'{icon} <{panel_url}|*{alert_name}*>'

    summary = alert['annotations'].get('summary')
    if summary:
        text += f'\n{summary}'
    description = alert['annotations'].get('description')
    if description:
        text += f'\n{description}'

    return {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': text
        }
    }


def build_fields_block(alert):
    fields = []

    for key, value in alert['annotations'].items():
        if key == 'summary' or key == 'description':
            continue
        fields.append({
            'type': 'mrkdwn',
            'text': f'*{key}:*\n{value}'
        })

    if len(fields) == 0:
        return None

    return {
        'type': 'section',
        'fields': fields
    }


def build_actions_block(alert):
    silence_url = alert['silenceURL']
    source_url = alert['generatorURL']
    dashboard_url = alert['dashboardURL']
    panel_url = alert['panelURL']

    return {
        'type': 'actions',
        'elements': [
            {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': ':no_bell: Silence',
                    'emoji': True
                },
                'style': 'danger',
                'url': silence_url
            },
            {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': ':information_source: Go to rule',
                    'emoji': True
                },
                'url': source_url
            },
            {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': ':bar_chart: Dashboard',
                    'emoji': True
                },
                'url': dashboard_url
            },
            {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': ':chart_with_upwards_trend: Panel',
                    'emoji': True
                },
                'url': panel_url
            }
        ]
    }


def build_image_block(alert):
    if alert['imageURL'] is None:
        return None

    return {
        'type': 'image',
        'image_url': alert['imageURL'],
        'alt_text': 'Grafana screenshot'
    }


def build_footer(alert):
    date = datetime.fromisoformat(alert['startsAt'])
    timestamp = int(date.timestamp())

    return {
        'type': 'context',
        'elements': [
            {
                'type': 'image',
                'image_url': 'https://grafana.com/static/assets/img/fav32.png',
                'alt_text': ''
            },
            {
                'type': 'mrkdwn',
                'text': f'Grafana  •  Started <!date^{timestamp}^{{date_short_pretty}} {{time_secs}}|-->'
            }
        ]
    }


# TODO: log uncaught

if __name__ == '__main__':
    app.run()
