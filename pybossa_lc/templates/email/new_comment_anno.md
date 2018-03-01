Hello,

The following comment has just been generated:

```
{{ annotation }}
```

Note that these messages can be disabled by setting EMAIL_COMMENT_ANNOTATIONS
to False in the main PYBOSSA settings file.

Thanks,
{{ config.BRAND }} Team

{% if config.get('CONTACT_TWITTER') %}
***

[Follow us on Twitter](http://twitter.com/{{ config['CONTACT_TWITTER'] }})
{% endif %}