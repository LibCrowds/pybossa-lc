Hello {{ user['fullname'] }},

You submitted some requests to create or update the
**{{ template['name'] }}** template. Unfortunately, we didn't think that the
proposed changes were suitable for the following reason:

{{ reason }}

Please get in touch at
[{{ config.CONTACT_EMAIL }}](mailto:{{ config.CONTACT_EMAIL }})
for further guidance.

Regards,

{{ config.BRAND }} Team
