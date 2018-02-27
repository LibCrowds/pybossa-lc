Dear {{ project.owner.fullname }},

As your project {{ project.name }} has been inactive for the last 3 months and we have unpublished it.

You can republish the project whenever you want, just access it on the server and click the publish button.

All the best,
{{ config.BRAND }} team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}