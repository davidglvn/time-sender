Time Entries Sender
===================

Simple script that take time entries from [Toggl](https://toggl.com) into [Freshdesk](https://freshdesk.com) ticket system.

## Default values
The script need this values to be set in order to work properly:
* TOOGL_DAY_TO_GET - Number of day to look back in Toggl time entries
* TOOGL_URL_PREFIX - Toggl API URL
* TOOGL_API_TOKEN - Toggl API token
* FRESHDESK_URL_PREFIX - Freshdesk API URL
* FRESHDESK_API_TOKEN - Freshdesk API token
* DEFAULT_EMAIL - Default email to use for new tickets
## Automatic Ticket creation
By default for each entry created new ticket in Freshdesk. After the ticket is created Toggl time entry receive two new tags:
* 'freshdesk' - meaning that this time entry already in Freshdesk
* 'ticket-DDDD' - 'ticket-' string with ticket ID

Freshdesk time entry store in the note Toggl time entry ID and description.
### Ticket requester
Script tries to find requester email for the ticket by taking Toggl time entry client name and compering to Freshdesk company name and picking first contact in the company contact list.

If the comparison fails, the script use DEFAULT_EMAIL variable value.

It's possible to add tag to Toggl time entry with email address as value, if such tag exists it will be used to create new ticket.

## Adding time entry to existing ticket
To add time entry to existing ticket add new tag in Toggl 'ticket-DDDD', where DDDD is ticket ID in Freshdesk

## Additional ticket options
When creating new ticket in Freshdesk the script look for type, status and priority tags.
### Type
* *Task* - default
* Question
* Incident
* Problem
* Lead
* Meeting
### Status
* *Open* - default
* Pending
* Resolved
* Closed - default for Meeting type
### Priority
* *Low* - default
* Medium
* High
* Urgent
