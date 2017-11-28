# -*- coding: utf8 -*-

import os
import json
import enki
import pytest
from pybossa_lc.core import create_app


flask_app = create_app()


@pytest.fixture
def app(request):
    ctx = flask_app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return flask_app


@pytest.fixture
def test_client(app):
    return app.test_client()


@pytest.fixture
def project():
    return enki.pbclient.DomainObject({
        "id": 1,
        "name": "Some Project",
        "short_name": "some_project",
        "webhook": "http://example.com",
    })


@pytest.fixture
def task(project):
    return enki.pbclient.DomainObject({
        "id": 42,
        "project_id": project.id,
        "info": {"url": "example.com", "title": "img.jpg"},
        "n_answers": 10,
        "quorum": 0,
        "calibration": 0,
        "state": "completed",
        "priority_0": 0.0
    })


@pytest.fixture
def result(project, task):
    return enki.pbclient.DomainObject({
        "id": 123,
        "project_id": project.id,
        "task_id": task.id,
        "info": None
    })


@pytest.fixture
def create_task_run(task, project):
    def create(id, info):
        return enki.pbclient.DomainObject({
            "id": id,
            "project_id": project.id,
            "info": info,
            "task_id": task.id,
        })
    return create


@pytest.fixture
def create_task_run_df(task, create_task_run):
    def create(task_run_info):
        tasks = [task]
        task_runs = []
        tr_data = {task.id: task_runs}

        # Create task runs using task run fixture as template
        for i in range(len(task_run_info)):
            tr = create_task_run(i, task_run_info[i])
            task_runs.append(tr)
        df = enki.dataframer.create_task_run_data_frames(tasks, tr_data)
        return df[task.id]
    return create


@pytest.fixture
def payload(project, task, result):
    load = dict(fired_at=u'2014-11-17 09:49:27',
                project_short_name=project.short_name,
                project_id=project.id,
                task_id=task.id,
                result_id=result.id,
                event='task_completed')
    return json.dumps(load)


@pytest.fixture
def processed_payload(payload, app):
    processed_pl = json.loads(payload)
    processed_pl['api_key'] = 'token'
    processed_pl['endpoint'] = app.config['ENDPOINT']
    processed_pl['doi'] = app.config['DOI']
    processed_pl['path'] = '/example'
    processed_pl['throttle'] = app.config['THROTTLE']
    processed_pl['mail_recipients'] = app.config['MAIL_RECIPIENTS']
    return processed_pl


@pytest.fixture
def select_annotation():
    def create(x, y, w, h):
        return {
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "id": "d008efa2-42e5-494e-b463-c7b9b6744b67",
            "type": "Annotation",
            "motivation": "tagging",
            "created": "2017-07-16T00:44:28.454Z",
            "generated": "2017-07-16T00:44:28.454Z",
            "target": {
                "source": "http://example.org/iiif/book1/canvas/p1",
                "selector": {
                    "conformsTo": "http://www.w3.org/TR/media-frags/",
                    "type": "FragmentSelector",
                    "value": "?xywh={0},{1},{2},{3}".format(x, y, w, h)
                }
            },
            "body": [
                {
                    "type": "TextualBody",
                    "purpose": "tagging",
                    "value": "title"
                },
                {
                    "type": "SpecificResource",
                    "purpose": "classifying",
                    "source": "http://purl.org/dc/terms/title"
                }
            ],
            "modified": "2017-07-16T13:53:18.795Z"
        }
    return create


@pytest.fixture
def comment_annotation():
    def create(comment):
        return {
            "body": {
                "type": "TextualBody",
                "purpose": "commenting",
                "value": comment,
                "format": "text/plain"
            },
            "motivation": "commenting",
            "target": "http://example.org/iiif/book1/canvas/p1",
            "created": "2017-08-31T10:09:55.082Z",
            "modified": "2017-08-31T10:09:57.777Z",
            "generated": "2017-08-31T10:09:55.082Z",
            "@context": "http://www.w3.org/ns/anno.jsonld",
            "type": "Annotation",
            "id": "4bad6560-9150-4558-bee7-a6b7fe055326"
        }
    return create