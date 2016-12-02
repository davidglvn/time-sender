import requests
import datetime
import json
import logging
import re

TOOGL_DAY_TO_GET = 3
TOOGL_URL_PREFIX = 'https://www.toggl.com/api/v8/'
TOOGL_API_TOKEN = ''
FRESHDESK_URL_PREFIX = 'https://YOUR_DOMAIN.freshdesk.com/api/v2/'
FRESHDESK_API_TOKEN = ''
DEFAULT_EMAIL = ''

freshdesk_status = {
    'Open': 2,
    'Pending': 3,
    'Resolved': 4,
    'Closed': 5
}
freshdesk_priority = {
    'Low': 1,
    'Medium': 2,
    'High': 3,
    'Urgent': 4
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)

# Check that we have default variables
try:
    if not (TOOGL_DAY_TO_GET and
            TOOGL_URL_PREFIX and
            TOOGL_API_TOKEN and
            FRESHDESK_URL_PREFIX and
            FRESHDESK_API_TOKEN and
            DEFAULT_EMAIL):
        logging.error('On of the Default Variable is not set')
        exit(2)
except NameError:
    logging.error('On of the Default Variable is not defined')
    exit(2)


def create_new_ticket():
    # Set some default info for the ticket
    email = DEFAULT_EMAIL
    ticket_type = 'Task'
    status = freshdesk_status['Open']
    priority = freshdesk_priority['Low']

    logging.debug('Going over tags')
    try:
        for tag in time_entry['tags']:
            logging.debug('Tag - {0}'.format(tag))
            # Check if we have special type for this time entry
            if tag.lower() in ['question', 'incident', 'task', 'problem', 'lead', 'meeting']:
                logging.debug('It\'s type tag')
                # If the time entry is for meeting, we will close the ticket
                if tag.lower() == 'meeting':
                    logging.debug('It\'s meeting tag')
                    status = freshdesk_status['Closed']
                ticket_type = tag.lower().title()
                continue
            # Check if we have some priority
            if tag.lower() in ['low', 'high', 'medium', 'urgent']:
                logging.debug('It\'s priority tag')
                priority = tag.lower().title()
                continue
            # Or maybe email address of the requester as tag
            if re.match(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', tag):
                logging.debug('It\'s an email')
                email = tag
    except KeyError:
        pass

    # Try to find email for the ticket in case there is no email in the tag
    if email == DEFAULT_EMAIL:
        # Get all the projects from Toggl
        get_projects_url = TOOGL_URL_PREFIX + 'projects/' + str(time_entry['pid'])
        logging.debug(get_projects_url)
        r_toggl_project = requests.get(get_projects_url,
                                       auth=(TOOGL_API_TOKEN, 'api_token'),
                                       headers=headers)
        if r_toggl_project.status_code not in [200, 201]:
            logging.error('Failed to get project data in Toggl API')
            logging.error(r_toggl_project.text)
        else:
            logging.debug(r_toggl_project.json())
            project_id = str(r_toggl_project.json()['data']['cid'])
            logging.debug('Found project id {0}'.format(project_id))
            # Get all the clients for the project in Toggl
            get_clients_url = TOOGL_URL_PREFIX + 'clients/' + project_id
            logging.debug(get_clients_url)
            r_toggl_client = requests.get(get_clients_url,
                                          auth=(TOOGL_API_TOKEN, 'api_token'),
                                          headers=headers)
            if r_toggl_client.status_code not in [200, 201]:
                logging.error('Failed to get client data in Toggl API')
                logging.error(r_toggl_client.text)
            else:
                logging.debug(r_toggl_client.json())
                client_name = r_toggl_client.json()['data']['name']
                logging.debug('Got client name in Toggl {0}'.format(client_name))
                # Get all the companies in Freshdesk
                get_companies_url = FRESHDESK_URL_PREFIX + 'companies'
                logging.debug(get_companies_url)
                r_freshdesk_companies = requests.get(get_companies_url,
                                                     auth=(FRESHDESK_API_TOKEN, 'api_token'),
                                                     headers=headers)
                if r_freshdesk_companies.status_code not in [200, 201]:
                    logging.error('Failed to get companies list in Freshdesk API')
                    logging.error(r_freshdesk_companies.text)
                else:
                    # Find Toggl client name in Freshdesk companies
                    for company in r_freshdesk_companies.json():
                        if client_name == company['name']:
                            logging.debug('Found the company in Freshdesk API {0}'.format(company['id']))
                            # Get all the contacts in Freshdesk for the company
                            get_contacts_url = FRESHDESK_URL_PREFIX + 'contacts?company_id=' + str(company['id'])
                            logging.debug(get_contacts_url)
                            r_freshdesk_contacts = requests.get(get_contacts_url,
                                                                auth=(FRESHDESK_API_TOKEN, 'api_token'),
                                                                headers=headers)
                            if r_freshdesk_contacts.status_code not in [200, 201]:
                                logging.error('Failed to get contacts for the company {0} in Freshdesk API'.
                                              format(company['id']))
                                logging.error(r_freshdesk_contacts.text)
                            else:
                                for contact in r_freshdesk_contacts.json():
                                    # Find the first email
                                    email = contact['email']
                                    logging.debug('Found user to create ticket with email {0}'.format(email))
                                    break
    # Generate new ticket payload
    new_ticket_payload = {
        'email': email,
        'subject': time_entry['description'],
        'type': ticket_type,
        'status': status,
        'priority': priority,
        'description': time_entry['description'],
        'responder_id': agent_id,
    }
    # Create new ticket in Freshdesk
    post_tickets_url = FRESHDESK_URL_PREFIX + 'tickets'
    r_freshdesk_tickets_post = requests.post(post_tickets_url,
                                             data=json.dumps(new_ticket_payload),
                                             auth=(FRESHDESK_API_TOKEN, 'api_token'),
                                             headers=headers)
    if r_freshdesk_tickets_post.status_code not in [200, 201]:
        logging.error('Failed to create ticket in Freshdesk API')
        logging.error(r_freshdesk_tickets_post.text)
        return False
    else:
        return str(r_freshdesk_tickets_post.json()['id'])

start_date = datetime.datetime.now() - datetime.timedelta(days=TOOGL_DAY_TO_GET)
end_date = datetime.datetime.now()
headers = {'content-type': 'application/json'}

logging.debug('Getting data from Toggl API')
get_url = TOOGL_URL_PREFIX + \
          'time_entries?start_date=' + start_date.strftime('%Y-%m-%dT%H%%3A%M%%3A%S%%2B00%%3A00') + \
          '&end_date=' + end_date.strftime('%Y-%m-%dT%H%%3A%M%%3A%S%%2B00%%3A00')
logging.debug(get_url)
r_toggl = requests.get(get_url,
                       auth=(TOOGL_API_TOKEN, 'api_token'),
                       headers=headers)

# Get Freshdesk agent ID
get_url = FRESHDESK_URL_PREFIX + 'agents/me'
logging.debug(get_url)
r_freshdesk = requests.get(get_url,
                           auth=(FRESHDESK_API_TOKEN, 'api_token'),
                           headers=headers)
if r_freshdesk.status_code not in [200, 201]:
    logging.error('Failed to Freshdesk agent ID')
    logging.error(r_freshdesk.text)
else:
    agent_id = int(r_freshdesk.json()['id'])
    logging.debug('Freshdesk agent ID {0}'.format(agent_id))

if r_toggl.status_code not in [200, 201]:
    logging.error('Failed to get data from Toggl API')
    logging.error(r_toggl.text)
    exit(1)

logging.debug('Running through the result')
for time_entry in r_toggl.json():
    logging.debug('Working on time entry {0}'.format(time_entry))
    try:
        if 'freshdesk' in time_entry['tags']:
            logging.info('This time entry already in Freshdesk')
            continue
    except KeyError:
        pass

    try:
        if 'new-ticket' not in time_entry['tags']:
            # Look for ticket ID in tags
            # If there is no tags KeyError exception is raised
            # If there is no ticket ID in tags IndexError exception is raised
            ticket_id = [tid for tid in time_entry['tags'] if 'ticket-' in tid][0][7:]
            logging.info('Found ticket ID #{0} in tag'.format(ticket_id))
        else:
            time_entry['tags'].remove('new-ticket')
            ticket_id = create_new_ticket()
    except KeyError:
        logging.info('Non Freshdesk time entry, skipping it')
        continue
    except IndexError:
        try:
            # Look if we have ticket ID in description, if there is not ticket ID in tags
            ticket_pattern = re.compile(r".*#(?P<ticket>[0-9]+).*")
            match = ticket_pattern.match(time_entry['description'])
            ticket_id = match.group("ticket")
            logging.info('Found ticket ID #{0} in description'.format(ticket_id))
        except AttributeError:
            continue
    finally:
        logging.info('Adding new time entry to ticket #{0}'.format(ticket_id))
        # Generate Freshdesk time format for duration
        hh = str(int(time_entry['duration'] / 3600))
        if len(hh) != 2:
            hh = '0' + hh
        mm = str(int(time_entry['duration'] % 3600 / 60))
        if len(mm) != 2:
            mm = '0' + mm

        # By default all the time entries in Toggl are billable, as I don't use pro version yet, I can't use this
        # billable function in Toggl, so I'm marking non billable with 'notbillable' tag
        billable = True
        new_toggl_time_entry = {'time_entry': {'tags': []}}
        # To identify time entries that were added to Freshdesk they marked with tag 'freshdesk'
        try:
            # Add the 'freshdesk' tag to existing tags
            time_entry['tags'].append('freshdesk')
            new_toggl_time_entry['time_entry']['tags'] = time_entry['tags']
            # Check if it's not billable time entry
            if 'notbillable' in time_entry['tags']:
                billable = False
        except KeyError:
            # If there is no tags, create new
            new_toggl_time_entry['time_entry']['tags'] = ['freshdesk']
        if 'ticket-' + str(ticket_id) not in new_toggl_time_entry['time_entry']:
            # If it's new ticket, add ticket ID to tags
            new_toggl_time_entry['time_entry']['tags'].append('ticket-' + str(ticket_id))
        # Generate new payload for Freshdesk time entry
        new_time_entry = {
            'note': 'Toggl ID :' + str(time_entry['id']) + '\n' + time_entry['description'],
            'agent_id': agent_id,
            'billable': billable,
            'executed_at': time_entry['start'][:-6],
            'time_spent': hh + ':' + mm
        }
        # Add new time entry to Freshdesk ticket
        post_url = FRESHDESK_URL_PREFIX + 'tickets/' + ticket_id + '/time_entries'
        logging.debug(post_url)
        r_freshdesk_post = requests.post(post_url,
                                         data=json.dumps(new_time_entry),
                                         auth=(FRESHDESK_API_TOKEN, 'api_token'),
                                         headers=headers)
        if r_freshdesk_post.status_code not in [200, 201]:
            logging.error('Failed to update ticket #{0} in Freshdesk with new time entry'.format(ticket_id))
            logging.error(r_freshdesk_post.text)
            logging.debug(new_time_entry)
        else:
            logging.info('New time entry was added to ticket #{0}'.format(ticket_id))
            logging.debug(new_time_entry)
            # If new time entry was added to Freshdesk, add 'freshdesk' tag and ticket id tag if needed to Toggl
            put_url = TOOGL_URL_PREFIX + 'time_entries/' + str(time_entry['id'])
            logging.debug(put_url)
            r_toggl_put = requests.put(put_url,
                                       data=json.dumps(new_toggl_time_entry),
                                       auth=(TOOGL_API_TOKEN, 'api_token'),
                                       headers=headers)
            if r_toggl_put.status_code not in [200, 201]:
                logging.error('Failed to add tag \'freshdesk\' to Toggl time entry {0}'.format(time_entry['id']))
                logging.error(r_toggl_put.text)
                logging.debug(time_entry)
                logging.debug(new_toggl_time_entry)
            else:
                logging.info('Added \'freshdesk\' tag to Toggl time entry {0}'.format(time_entry['id']))
                logging.debug(r_toggl_put.text)
                logging.debug(new_toggl_time_entry)
