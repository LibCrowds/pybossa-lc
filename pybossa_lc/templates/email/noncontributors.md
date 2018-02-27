Hi, {{ user['fullname'] }}!

We notice you signed up for {{config.BRAND}} some time ago but never contributed.
It would be great if you could come and help us in improving access to the collections of the British Library!

[Click here to see the projects that need your help.]({{ url_for('project.index') }})

Thanks,
{{ config.BRAND }} Team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}