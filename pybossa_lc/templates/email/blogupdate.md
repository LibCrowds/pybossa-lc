# New Blog Post: {{blog['title']}} by {{blog['owner']['name']}} [1]
{{ blog['body'] | striptags }}

[1]{{ url_for('project.show_blogpost', short_name=blog.project.short_name, id=blog.id, _external=True) }}

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}