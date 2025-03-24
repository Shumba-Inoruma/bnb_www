import frappe
from frappe import _
from frappe.utils.response import build_response
import random
import requests
import os
from werkzeug.utils import secure_filename
from frappe.utils.file_manager import save_file,delete_file
from frappe.utils import now_datetime, time_diff_in_seconds


# ---------------------------------------------this is the block for users-------------------------------------------------------
VALID_ROLES = ["bnb_agents", "bnb_clients", "bnb_property_owners"]

# Dictionary for email verification
VERIFICATION_CODES = {
    "chirovemunyaradzi@gmail.com": "1234",
    # Add other emails and verification codes here as needed
}

@frappe.whitelist(allow_guest=True)
def create_user(email, first_name, last_name, password, role, phone_number, verification_code):
    """Creates a new user in bnb_users and assigns a role, with email verification."""
    
    # Validation: Ensure role is valid
    if role not in VALID_ROLES:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Invalid role: {}. Allowed roles are: {}".format(role, ', '.join(VALID_ROLES)))
        return

    # Validation: Check required fields
    if not email or not password or not verification_code:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Email, Password, and Verification Code are required fields")
        return
    
    # Validation: Ensure first_name, last_name, and phone_number are provided
    if not first_name or not last_name or not phone_number:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("First Name, Last Name, and Phone Number are mandatory fields.")
        return
    
    # Check if the verification code matches the one in the dictionary
    # if VERIFICATION_CODES.get(email) != verification_code:
    #     frappe.local.response["status_code"] = 400
    #     frappe.local.response["message"] = _("Verification failed")
    #     return

    # Check if the phone number already exists in the custom bnb_users Doctype
    if frappe.db.exists('bnb_users', {'phone_number': phone_number}):
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("User with phone number {} already exists".format(phone_number))
        return
     # Check if the phone number already exists in the custom bnb_users Doctype
    if frappe.db.exists('bnb_users', {'email': email}):
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("User with email {} already existss".format(email))
        return
    
    res=verify_code(phone_number=phone_number,verification=verification_code)
    print(res)
    if res['status_code']==200:
        try:
            # Create the user in the custom bnb_users Doctype
            user = frappe.get_doc({
                "doctype": "bnb_users",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "enabled": 1,
                "roles": [{"role": role}],  # Single role as a dictionary
                "password": password  # Store the password directly
            })
            
            # Insert the user (with password)
            user.insert(ignore_permissions=True)

            # Success response
            frappe.local.response["status_code"] = 201
            frappe.local.response["message"] = _("User created successfully: {0}".format(email))
            frappe.local.response["data"] = {"user_email": email, "role": role}

        except Exception as e:
            frappe.local.response["status_code"] = 500
            frappe.local.response["message"] = _("Failed to create user. Error: {0}".format(str(e)))
            frappe.local.response["data"] = {}

    else:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _(res['message'])
        return




@frappe.whitelist(allow_guest=True)
def verify_code(phone_number: str, verification: str) -> dict:
    try:
        # Check if the verification entry exists
        existing_verification = frappe.db.exists("bnb_verification", {
            "phone_number": phone_number,
            "verification_code": verification
        })

        if not existing_verification:
            return {
                'status_code': 404,
                'message': 'Verification entry not found.'
            }

        # Fetch the creation time of the existing entry
        creation_time = frappe.db.get_value('bnb_verification', existing_verification, 'creation_date')

        # Calculate time difference in seconds
        time_difference = time_diff_in_seconds(now_datetime(), creation_time)

        fifteen_minutes_in_seconds = 15 * 60

        if time_difference > fifteen_minutes_in_seconds:
            print("mmm time")
            return {
                'status_code': 403,
                'message': 'Verification code expired.'
            }

        return {
            'status_code': 200,
            'message': 'Verification successful.'
        }

    except Exception as e:
        return {
            'status_code': 500,
            'message': f'Error: {str(e)}'
        }


@frappe.whitelist(allow_guest=True)
def bnb_verification(phone_number):
    """Generates a 4-digit verification code for the provided phone number, stores it in the 'bnb_verification' Doctype, and overrides if it exists."""

    # Generate a random 4-digit verification code
    verification_code = str(random.randint(1000, 9999))

    # Check if a verification entry for this phone number already exists
    existing_verification = frappe.db.exists("bnb_verification", {"phone_number": phone_number})
    
    if existing_verification:
        # If exists, delete the existing record before creating a new one
        frappe.delete_doc("bnb_verification", existing_verification)

    try:
        print("yessssssssssssss")
        response=send_whatsapp_message(phone_number=phone_number,variable_value=verification_code)
        print(response['status_code'])
        
        if str(response.get("status_code"))=="200":

            # Create a new verification entry
            verification_entry = frappe.get_doc({
                "doctype": "bnb_verification",
                "phone_number": phone_number,
                "verification_code": verification_code,
                "creation_date": frappe.utils.now()
            })

            # Insert the verification entry
            verification_entry.insert(ignore_permissions=True)
            verification_entry.save()
            
                

            # Send the verification code via SMS (integrate SMS API here)
            # Example: send_sms(phone_number, verification_code)

            return {
                "status_code": 200,
                "message": _("Verification code generated and sent successfully."),
                "data": {
                    "phone_number": phone_number,
                    "verification_code": verification_code
                }
            }
        else:
               return {
                "status_code": 403,
                "message": _("Please check the whatsapp number and verify"),
                "data": {
                    "phone_number": phone_number,
                    "verification_code": verification_code
                }
            }

    except Exception as e:
        return {
            "status_code": 500,
            "message": _("Failed to generate or store verification code. Error: {0}".format(str(e))),
            "data": {}
        }


# Facebook API credentials
FACEBOOK_ACCESS_TOKEN = 'EAAHRrLF2ecUBO6K3j3z7BaQHJSIZCMwlgT1bZBViZBnj4nL8WkmzYroFZA5qwLbDg8dF0yFGmZAAeXM6M2uFF32HwmFhyA0c69RUG4xwBmPUdpspryf8VApwnUiOZBcVvO6CRZCg0kM2L4nl8weNIiphh8TKapFiCIDXRckIfQFx9dG939kqUZAtW36B8bTVSDDBBgZDZD'
FACEBOOK_PHONE_NUMBER_ID = '621029511088946'
FACEBOOK_WHATSAPP_API_URL = 'https://graph.facebook.com/v16.0/{}/messages'.format(FACEBOOK_PHONE_NUMBER_ID)

@frappe.whitelist(allow_guest=True)
def send_whatsapp_message(phone_number,variable_value):
    print("yyyy")

    # phone_number="2637840999216"
    # variable_value=2321
    """Sends a WhatsApp message with a predefined template from Facebook WhatsApp Cloud API."""
    
    # Your WhatsApp template name (approved template)
    template_name = 'test_number'  # Replace with your actual template name

    # Prepare the data for the API request
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,  # Phone number in international format, without 'whatsapp:'
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en"  # Use the language code of the template
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": variable_value  # Replace the placeholder in the template with the variable
                        }
                    ]
                }
            ]
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
                "status_code": 200
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
    

@frappe.whitelist(allow_guest=True)
def get_all_users():
    """Fetches all users from the 'bnb_users' Doctype."""
    
    try:
        # Query the 'bnb_users' Doctype to fetch all user records
        users = frappe.get_all('bnb_users', fields=["email", "first_name", "last_name", "phone_number", "role"])

        if not users:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("No users found")
            frappe.local.response["data"] = []
            return

        # Success response with user data
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Users fetched successfully.")
        frappe.local.response["data"] = users

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to fetch users. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

_

@frappe.whitelist(allow_guest=True)
def get_user_by_email_or_phone(email=None, phone_number=None):
    """Fetches a user from the 'bnb_users' Doctype by either email or phone number."""
    
    try:
        # Ensure at least one of email or phone_number is provided
        if not email and not phone_number:
            frappe.local.response["status_code"] = 400
            frappe.local.response["message"] = _("Either email or phone number must be provided.")
            frappe.local.response["data"] = {}
            return

        # Prepare filters
        filters = {}
        if email:
            filters["email"] = email
        if phone_number:
            filters["phone_number"] = phone_number

        # Query the 'bnb_users' Doctype to fetch user records based on filters
        users = frappe.get_all('bnb_users', filters=filters, fields=["email", "first_name", "last_name", "phone_number", "role"])

        if not users:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("No user found with the provided email or phone number.")
            frappe.local.response["data"] = {}
            return

        # Success response with user data
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("User fetched successfully.")
        frappe.local.response["data"] = users[0]  # Assuming a single user is returned

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to fetch user. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

# ---------------------------------------------this is the end block for user-------------------------------------------------------



# ---------------------------------------------this is the block for lising-------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def create_bnb_listing(listing_name, location, price, listing_agent, property_owner, service, description):
    """Creates a new bnb_listing after verifying the agent and property owner."""

    VALID_SERVICES = ["Renting", "Student Accommodation", "Lodge", "Other"]
    
    # Validate service type
    if service not in VALID_SERVICES:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Invalid service type. Allowed services are: {}".format(', '.join(VALID_SERVICES)))
        return

    # Validate if the assigned agent exists and has the role 'bnb_agents'
    agent = frappe.db.get_value('bnb_users', {'email': listing_agent, 'role': 'bnb_agents'}, 'name')
    if not agent:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Agent not found or does not have the 'bnb_agents' role.")
        return

    # Validate if the property owner exists and has the role 'bnb_property_owners'
    owner = frappe.db.get_value('bnb_users', {'email': property_owner, 'role': 'bnb_property_owners'}, 'name')
    if not owner:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Property owner not found or does not have the 'bnb_property_owners' role.")
        return

    try:
        # Create the new listing using frappe.get_doc()
        listing = frappe.get_doc({
            "doctype": "bnb_listings",
            "listing_name": listing_name,
            "location": location,
            "price": price,
            "listing_agent": listing_agent,
            "listing_owner": property_owner,
            "service": service,
            "description": description
        })
        
        # Insert the document and save
        listing.insert(ignore_permissions=True)
        listing.save()

        # Return success response with listing ID
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Listing created successfully.")
        frappe.local.response["data"] = {"listing_id": listing.name}

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to create listing. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

@frappe.whitelist(allow_guest=True)
def get_all_bnb_listings():
    """Fetches all the properties (listings) from the bnb_listings Doctype."""
    try:
        # Fetch all the properties from the 'bnb_listings' Doctype
        listings = frappe.get_all('bnb_listings', fields=["name", "listing_name","listing_owner","listing_agent", "location", "price", "service", "description"])
        
        # Check if listings are available
        if not listings:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("No listings found.")
            return
        
        # Return success response with the list of properties
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Listings fetched successfully.")
        frappe.local.response["data"] = {"listings": listings}
    
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to fetch listings. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

@frappe.whitelist(allow_guest=True)
def get_bnb_listing_by_name(listing_name):
    """Fetches a property (listing) by its listing_name (ID) from the bnb_listings Doctype."""
    try:
        # Fetch the property based on the listing_name
        listing = frappe.get_all('bnb_listings', filters={'name': listing_name}, fields=["name", "listing_name", "location", "price", "service", "description"])
        
        # Check if the listing exists
        if not listing:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("Listing not found.")
            return
        
        # Return success response with the property details
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Listing fetched successfully.")
        frappe.local.response["data"] = {"listing": listing[0]}  # Since get_all returns a list, we fetch the first item
    
    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to fetch listing. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

@frappe.whitelist(allow_guest=True)
def delete_bnb_listing(name):
    """Deletes a property (listing) by its listing_name (ID) from the bnb_listings Doctype."""
    try:
        # Fetch the property based on the listing_name
        listing = frappe.get_value('bnb_listings', {'name':name}, 'name')
        
        # Check if the listing exists
        if not listing:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("Listing not found.")
            return
        
        # Delete the listing
        frappe.delete_doc('bnb_listings',name)

        # Return success response
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Listing deleted successfully.")
        frappe.local.response["data"] = {}

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to delete listing. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

@frappe.whitelist(allow_guest=True)
def edit_bnb_listing(name,listing_name, listing_agent=None, listing_owner=None, service=None, description=None, location=None, price=None):
    """Edit an existing bnb_listing by its listing_name (ID)."""
    
    try:
        # Fetch the property (listing) based on listing_name
        listing = frappe.get_doc('bnb_listings', name)
        
        # Check if the listing exists
        if not listing:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("Listing not found.")
            return
        
        # Update fields if provided
        if listing_agent:
            agent = frappe.db.get_value('bnb_users', {'email': listing_agent, 'role': 'bnb_agents'}, 'name')
            if not agent:
                    frappe.local.response["status_code"] = 400
                    frappe.local.response["message"] = _("Agent not found or does not have the 'bnb_agents' role.")
                    return
            else:
                 listing.listing_agent = listing_agent

        # Validate if the property owner exists and has the role 'bnb_property_owners'
               
        if listing_name:
                listing.listing_name = listing_name  
        
        if listing_owner:
            owner = frappe.db.get_value('bnb_users', {'email': listing_owner, 'role': 'bnb_property_owners'}, 'name')
            if not owner:
                frappe.local.response["status_code"] = 400
                frappe.local.response["message"] = _("Property owner not found or does not have the 'bnb_property_owners' role.")
                return
            else:
                listing.listing_owner = listing_owner
        
        if service:
            VALID_SERVICES = ["Renting", "Student Accommodation", "Lodge", "Other"]
            if service not in VALID_SERVICES:
                frappe.local.response["status_code"] = 400
                frappe.local.response["message"] = _("Invalid service type. Allowed services are: {}".format(', '.join(VALID_SERVICES)))
                return
            listing.service = service
        
        if description:
            listing.description = description
        
        if location:
            listing.location = location
        
        if price:
            listing.price = price
        
        # Save the updated listing
        listing.save(ignore_permissions=True)

        # Return success response with listing ID
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Listing updated successfully.")
        frappe.local.response["data"] = {"listing_id": listing.name}

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to update listing. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}

# ---------------------------------------------this is the end block for lising-------------------------------------------------------


# ---------------------------------------------this is the block for images-------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def upload_image():
    """Upload image to the system and save the URL in Images doctype."""
    
    # Get the image file from the request
    image_file = frappe.request.files.get("image_file")
    property_name = frappe.local.request.form.get("property_name")  # Get property name

    if not image_file:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("No image file found in the request.")
        frappe.local.response["data"] = {}
        return
    
    if not property_name:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("No property name found in the request.")
        frappe.local.response["data"] = {}
        return

    # Validate image type
    allowed_extensions = ["jpg", "jpeg", "png"]
    file_extension = image_file.filename.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("Invalid image format. Allowed formats: jpg, jpeg, png.")
        frappe.local.response["data"] = {}
        return

    try:
        # Secure the file name
        filename = secure_filename(image_file.filename)
        
        # Read the file content (this solves the 'no len()' error)
        file_content = image_file.read()

        # Save the image in Files section
        file_doc = save_file(
            filename,  # File name
            file_content,  # The actual file content (not the stream)
            "File",  # Save to "File" DocType
            "Images"  # The folder in which to store the file (optional)
        )

        # Get the file URL (file_doc.file_url) from the saved file
        image_url = file_doc.file_url

        # Save the image URL in the 'Images' doctype
        image_doc = frappe.get_doc({
            "doctype": "bnb_image",  # The doctype to save the image in
            "image": image_url,  # Save the URL of the image
            "listing_name": property_name,  # Link to the property (e.g., 'bnb_listing')
        })
        
        # Insert the image record
        image_doc.insert(ignore_permissions=True)

        # Return success response with image ID and URL
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Image uploaded and linked to property successfully.")
        frappe.local.response["data"] = {
            "image_id": image_doc.name,
            "file_url": image_url  # URL of the uploaded image
        }

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to upload image. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}



@frappe.whitelist(allow_guest=True)
def delete_image(image_id):
    """Delete an image record and the associated file based on the URL."""

    if not image_id:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("No image ID provided.")
        frappe.local.response["data"] = {}
        return
    
    try:
        # Get the image record from the Images doctype
        image_doc = frappe.get_doc("bnb_image", image_id)
        
        if not image_doc:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("Image record not found.")
            frappe.local.response["data"] = {}
            return

        # Get the file URL stored in the image record
        image_url = image_doc.image
        
        # Check if the file URL exists in the Files doctype
        file_doc = frappe.get_doc("File", {"file_url": image_url})
        print(file_doc)
        print(file_doc.name)
        
        # needs some work
        if file_doc:
            # Delete the associated file
            delete_file(file_doc.name)
        
        # # Delete the image record from the Images doctype
        # image_doc.delete()

        # Return success response
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Image and associated file deleted successfully.")
        frappe.local.response["data"] = {}

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to delete image. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}


@frappe.whitelist(allow_guest=True)
def get_images_by_listing(listing_name):
    """Get all images associated with a property based on the property ID."""
    
    if not listing_name:
        frappe.local.response["status_code"] = 400
        frappe.local.response["message"] = _("No property ID provided.")
        frappe.local.response["data"] = {}
        return

    try:
        # Get all images that have the property_name equal to the given property_id
        images = frappe.get_all("bnb_image", filters={"listing_name": listing_name}, fields=["name", "image"])
        
        if not images:
            frappe.local.response["status_code"] = 404
            frappe.local.response["message"] = _("No images found for this listing.")
            frappe.local.response["data"] = {}
            return
        
        # Return success response with image data
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = _("Images retrieved successfully.")
        frappe.local.response["data"] = {
            "images": images
        }

    except Exception as e:
        frappe.local.response["status_code"] = 500
        frappe.local.response["message"] = _("Failed to retrieve images. Error: {0}".format(str(e)))
        frappe.local.response["data"] = {}
        frappe.log_error(f"Error during image retrieval for property {listing_name}: {str(e)}", "get_images_by_property")
