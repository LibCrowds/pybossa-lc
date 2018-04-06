# -*- coding: utf8 -*-

# SPA frontend endpoints
PROJECT_TMPL_ENDPOINT = u'/admin/project/{}/template'

# Extra tasks to run when the application is started or restarted
EXTRA_STARTUP_TASKS = {
    'check_for_invalid_templates': False,
    'populate_empty_results': False
}

# The main LibCrowds GitHub repo (used as the Web Annotation generator IRI)
GITHUB_REPO = 'https://github.com/LibCrowds/libcrowds'

# The user ID used to make automated announcements
ANNOUNCEMENT_USER_ID = 1

# Email all comment annotations to administrators
EMAIL_COMMENT_ANNOTATIONS = False
