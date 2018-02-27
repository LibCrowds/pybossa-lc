Hello {{ user['fullname'] }},

As you have updated your email address at {{ config.BRAND }} we need to verify that you
are indeed the owner of this address. To do so, please visit the URL below:

[Click here to validate your new e-mail address][confirm]

[confirm]: {{ confirm_url }}

Regards,

{{ config.BRAND }} Team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}
