# -*- coding: utf8 -*-

# SPA frontend endpoints
PROJECT_TMPL_ENDPOINT = u'/admin/project/{}/template'

# Extra tasks to run when the application is started or restarted
EXTRA_STARTUP_TASKS = {
    'check_for_invalid_templates': False,
    'populate_empty_results': False,
    'reanalyse_all_results': False,
    'remove_bad_volumes': False
}

# The main LibCrowds GitHub repo (used as the Web Annotation generator IRI)
GITHUB_REPO = 'https://github.com/LibCrowds/libcrowds'
