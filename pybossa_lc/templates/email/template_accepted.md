Hello {{ user['fullname'] }},

You submitted some requests to create or update the
**{{ template['name'] }}** template. Good news, the proposed
 changes have been accepted!

To create a project using your new template visit
[{{ config.SPA_SERVER_NAME }}]({{ config.SPA_SERVER_NAME }}) and
select the **New Project** option from the main menu (click the
Menu button in the navigation bar).

Please get in touch at
[{{ config.CONTACT_EMAIL }}](mailto:{{ config.CONTACT_EMAIL }})
for further guidance.

Regards,

{{ config.BRAND }} Team
