Hello {{ user.fullname }},

We received a request to reset your {{ config.BRAND }} password.

[Click here to reset your password.][recover]

[recover]: {{ recovery_url }}

If you did not make this request, please ignore this email.

Regards,
{{ config.BRAND }} Team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}