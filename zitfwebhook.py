import frappe
from frappe import _
from frappe.utils.response import build_response
import random
import requests
import os
from werkzeug.utils import secure_filename
from frappe.utils.file_manager import save_file,delete_file
from frappe.utils import now_datetime, time_diff_in_seconds
import hashlib
import frappe
from frappe import _
import json
import re
# import grpc
# import africom_cdma.africom_cdma.doctype.grpc_gateways.guroo_users as guroo
# import africom_cdma.africom_cdma.doctype.grpc_gateways.guroo_payments as guroo2
import random
import string
import requests
import werkzeug.utils
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.local import LocalProxy
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file
from threading import Thread
import asyncio


# Facebook API credentials
FACEBOOK_ACCESS_TOKEN = 'EAAHRrLF2ecUBO6K3j3z7BaQHJSIZCMwlgT1bZBViZBnj4nL8WkmzYroFZA5qwLbDg8dF0yFGmZAAeXM6M2uFF32HwmFhyA0c69RUG4xwBmPUdpspryf8VApwnUiOZBcVvO6CRZCg0kM2L4nl8weNIiphh8TKapFiCIDXRckIfQFx9dG939kqUZAtW36B8bTVSDDBBgZDZD'
FACEBOOK_PHONE_NUMBER_ID = '621029511088946'
FACEBOOK_WHATSAPP_API_URL = 'https://graph.facebook.com/v16.0/{}/messages'.format(FACEBOOK_PHONE_NUMBER_ID)


@frappe.whitelist(allow_guest=True)
def whatsapp_reply(message,to):
    print("Sending message...")
    
    # Phone number to send the message to (in international format)
    phone_number = to  # Replace with the actual phone number
    
    # Variable for the message content (customizable)
    variable_value = message

    # Prepare the data for the API request
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,  # Phone number in international format
        "type": "text",  # Directly sending a text message, not a template
        "text": {
            "body": variable_value  # The actual message content
        }
    }

    # Set the headers for the request
    headers = {
        'Authorization': 'Bearer {}'.format(FACEBOOK_ACCESS_TOKEN),
        'Content-Type': 'application/json',
    }

    # Send the request to the Facebook API
    try:
        response = requests.post(FACEBOOK_WHATSAPP_API_URL, json=payload, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            return {
                "status_code": 200,
                "message": "Message sent successfully!"
            }
        else:
            error_message = response.json().get("error", {}).get("message", "Unknown error")
            return {
                "status_code": response.status_code,
                "message": _("Failed to send WhatsApp message. Error: {0}".format(error_message)),
                "data": {}
            }

    except Exception as e:
        return {
            "status_code": 500,
            "message": _("Failed to send WhatsApp message. Error: {0}".format(str(e))),
            "data": {}
        }























async def async_process(profile_name, wa_id, message, message_type,message_id):
    try:
        print(f"**********look**************************")
        print(f"Profile Name: {profile_name}")
        print(f"WA ID: {wa_id}")
        print(f"Raw Message: {message} (Type: {type(message)})")
        print(f"Message Type: {message_type}")


        print(f"Processed Message: {message} (Type: {type(message)})")

        # Simulate heavy processing (Replace this with actual processing logic)
        await asyncio.sleep(1)  # Example delay for processing
        process(profile_name, wa_id, message, message_type,message_id)
    except Exception as e:
        print(f"Error processing message: {e}")


@frappe.whitelist(allow_guest=True)
def webhook():
    print("***********INCOMING**********************")
    if frappe.request.method == "GET":
        query_params = frappe.request.args
        mode = query_params.get("hub.mode")
        verify_token = query_params.get("hub.verify_token")
        challenge = query_params.get("hub.challenge")
        
        # Verify the subscription request
        if mode == "subscribe" and verify_token == 'EAAHRrLF2ecUBO6K3j3z7BaQHJSIZCMwlgT1bZBViZBnj4nL8WkmzYroFZA5qwLbDg8dF0yFGmZAAeXM6M2uFF32HwmFhyA0c69RUG4xwBmPUdpspryf8VApwnUiOZBcVvO6CRZCg0kM2L4nl8weNIiphh8TKapFiCIDXRckIfQFx9dG939kqUZAtW36B8bTVSDDBBgZDZD':  # Replace with environment variable or secure storage
            return Response(challenge, status=200, content_type="text/plain")
        else:
            return Response("Forbidden", status=403)
    
    elif frappe.request.method == "POST":
        try:
            data = frappe.request.get_json()
            print(f"***********maiwee**********{data}")
            if not data:
                return Response("No Data", status=400)

            entries = data.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [])
                    
                    for contact in contacts:
                        profile_name = contact.get("profile", {}).get("name", "Unknown")
                        wa_id = contact.get("wa_id", "Unknown")

                        # Iterate through each message
                        for message in messages:
                            message_type = message.get("type", "unknown")
                            message_id = message.get("id", "unknown")

                            if message_type == "text":
                                    asyncio.run(async_process(profile_name, wa_id, message, message_type,message_id))
                                    return Response("OK", status=200)
                            

                            elif message_type == "button":
                                asyncio.run(async_process(profile_name, wa_id, message,message_type,message_id))
                                return Response("OK", status=200)  


                            elif message_type == "interactive":
                                print(f"----------------------------interactive")
                                interactive_type = message.get("interactive", {}).get("type", "")
                                if interactive_type == "list_reply":
                                    asyncio.run(async_process(profile_name, wa_id, message,message_type,message_id))
                                return Response("OK", status=200)
            
            # Return 200 OK to acknowledge the webhook
            return Response("OK", status=200)

        except Exception as e:
            return Response("Error processing webhook", status=500)

    else:
        # Unsupported HTTP method
        return Response("Method Not Allowed", status=405)

                           







































































programs = """
🎉 Here are the Programs for ZITF Conference Attendance 📋

1. 📍 ZITF Check-In
   - Track attendees as they arrive at the event.

2. 📅 Daily Attendance 📝
   - Monitor who's present each day of the conference.

3. 🎫 Badge Scan Tracker
   - Keep a record of attendees via QR codes or badge scans.

4. 👥 Guest Presence Monitor
   - Specifically for VIPs, exhibitors, and special guests.

5. ⏰ Time-In / Time-Out
   - Track the exact arrival and departure times of attendees.

6. 🧾 Registration & Attendance Log
   - Comprehensive log of both registrations and attendance.

7. 📊 Attendance Dashboard
   - Real-time stats and charts displaying attendee presence.

8. 📌 Session Checkpoint
   - Track attendance for specific sessions or workshops.

9. 📍 Exhibit Zone Tracker
   - Monitor which exhibit zones attendees visit.

10. ✅ ZITF Attendee Verified
   - Confirm an attendee's presence and authorization status.
"""



def process(profile_name, id, message,message_type,message_id):
    to = message.get("from")
    if message_type == 'text':
        message_text = message.get("text")
        message_body = message_text.get("body", "") if isinstance(message_text, dict) else ""
        message = message_body.strip().lower()

        if message.lower() in ["yes"]:
            if frappe.db.exists("zitf", {"whatsapp_number": to}):
                whatsapp_reply(message=programs,to=to)
            else:
                whatsapp_reply(message="👋 Hello! Kindly register your number with us to enjoy our services 🎉.\n https://imba.durihub.co.zw/zitf-conference-register/new",to=to)
        else:
            whatsapp_reply(to=to, message="⚠️ Invalid option. Please type *\"Yes\"* to receive programs.")
            return

            









