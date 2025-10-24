Upgraded the Django framework to version 5. Manual database upgrade for the 
django_celery_results extenstion required for move to version 2.6.0. Plase note
that CDTS must be reamin at version 5.0.1 for now.
Note that for Django-celery-results version 2.6.0, a database change is required.

  python .\manage.py migrate django_celery_results --fake zero
  python .\manage.py migrate django_celery_results 0001
