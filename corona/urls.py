from django.urls import path
from corona import views

urlpatterns = [
    # path('map<int:num>', views.maps, name='num'),
    path('2x2box', views.screen2, name='2x2box'),
    path('2x2box/<str:continent>', views.screen2, name='continent'),
    path('2x2box/<str:continent>/regression', views.regression_chart, name='regression'),
    path('2x2box/<str:continent>/<str:case_a>', views.screen2, name='regression'),
    path('2x2box/<str:continent>/<str:case_a>/regression', views.regression_chart, name='regression'),
    path('2x2box/<str:continent>/<str:case_a>/<str:case_b>', views.screen2, name='regression'),
    path('2x2box/<str:continent>/<str:case_a>/<str:case_b>/regression', views.regression_chart, name='regression'),
    path('', views.index, name='home'),
    path('maps', views.show_map, name='map_iframe'),

    # path('map', views.index, name='map'),
    path('<str:continent>', views.index, name='map'),
    path('<str:continent>/<str:cases>', views.index, name='map'),

]
