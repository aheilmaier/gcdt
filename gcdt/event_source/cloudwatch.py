# -*- coding: utf-8 -*-
# Copyright (c) 2014, 2015 Mitch Garnaat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import base
import logging
import uuid

LOG = logging.getLogger(__name__)


class CloudWatchEventSource(base.EventSource):

    #def __init__(self, context, config):
    def __init__(self, awsclient, config):
        #super(CloudWatchEventSource, self).__init__(context, config)
        super(CloudWatchEventSource, self).__init__(awsclient, config)
        self._events = awsclient.get_client('events')
        self._lambda = awsclient.get_client('lambda')
        if 'arn' in config:
            self._name = config['arn'].split('/')[-1]
        elif 'name' in config:
            self._name = config['name']
        #self._context = context
        self._config = config

    def exists(self, function):
        return self.get_rule()

    def get_rule(self):
        response = self._events.list_rules(NamePrefix=self._name)
        LOG.debug(response)
        if 'Rules' in response:
            for r in response['Rules']:
                if r['Name'] == self._name:
                    return r
        return None

    def add(self, function):
        function_name = base.get_lambda_name(function)
        kwargs = {
            'Name': self._name,
            'State': 'ENABLED'  #if self.enabled else 'DISABLED'
        }
        if 'schedule' in self._config:
            kwargs['ScheduleExpression'] = self._config['schedule']
        if 'pattern' in self._config:
            kwargs['EventPattern'] = self._config['pattern']
        if 'description' in self._config:
            kwargs['Description'] = self._config['description']
        if 'role_arn' in self._config:
            kwargs['RoleArn'] = self._config['role_arn']
        try:
            response = self._events.put_rule(**kwargs)
            LOG.debug(response)
            self._config['arn'] = response['RuleArn']
            existingPermission={}
            try:
                response = self._lambda.get_policy(FunctionName=function_name)
                existingPermission = self._config['arn'] in str(response['Policy'])
            except Exception:
                LOG.debug('CloudWatch event source permission not available')

            if not existingPermission:
                response = self._lambda.add_permission(
                     FunctionName=function_name,
                     StatementId=str(uuid.uuid4()),
                     Action='lambda:InvokeFunction',
                     Principal='events.amazonaws.com',
                     SourceArn=self._config['arn']
                )
                LOG.debug(response)
            else:
                LOG.debug('CloudWatch event source permission already exists')
            response = self._events.put_targets(
                 Rule=self._name,
                 Targets=[{
                     'Id': function_name,
                     'Arn': function
                 }]
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to put CloudWatch event source')

    def update(self, function):
        self.add(function)

    def remove(self, function):
        function_name = base.get_lambda_name(function)
        LOG.debug('removing CloudWatch event source')
        try:
            rule = self.get_rule()
            if rule:
                response = self._events.remove_targets(
                    Rule=self._name,
                    Ids=[function_name]
                )
                LOG.debug(response)
                response = self._events.delete_rule(Name=self._name)
                LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove CloudWatch event source %s', self._name)

    def status(self, function):
        function_name = base.get_lambda_name(function)
        LOG.debug('status for CloudWatch event for %s', function_name)
        return self._to_status(self.get_rule())

    def enable(self, function):
        if self.get_rule():
            self._events.enable_rule(Name=self._name)

    def disable(self, function):
        if self.get_rule():
            self._events.disable_rule(Name=self._name)

    def _to_status(self, rule):
        if rule:
            return {
                'EventSourceArn': rule['Arn'],
                'State': rule['State']
            }
        return None
