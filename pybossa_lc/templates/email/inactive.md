Hi, {{ user['fullname'] }}!

We notice you haven’t visited {{config.BRAND}} for more than three months.
It would be great if you could come and help us again and improve access to the
collections of the British Library!

[Click here to see the projects that need your help.]({{ url_for('project.index') }})

Thanks,
{{ config.BRAND }} Team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}