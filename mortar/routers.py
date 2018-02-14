"""
BSD 3-Clause License

Copyright (c) 2018, North Carolina State University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. The names "North Carolina State University", "NCSU" and any trade‐name,
   personal name, trademark, trade device, service mark, symbol, image, icon,
   or any abbreviation, contraction or simulation thereof owned by North
   Carolina State University must not be used to endorse or promoteproducts
   derived from this software without prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

class AnalysisRouter(object):
    '''A router to control what the user can interact with through SQL Explorer'''
    def db_for_read(self, model, **hints):
        if model._meta.db_table == 'annotations':
            return 'explorer'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.db_table == 'anotations':
            return 'explorer'
        return None
 
    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.db_table == 'annotations' or obj2._meta.db_table == 'annotations':
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'explorer':
            return model_name == 'annotation'
        elif model_name == 'annotation':
            return False
        return None
