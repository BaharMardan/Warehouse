from app.routers.ghabz import receipt_locations


def test_all_unique_locations_are_kept_per_hs_code():
    rows=[{'hscode':' A ','anbar_name':'1','tagh_name':'10'},
          {'hscode':'A','anbar_name':'2','tagh_name':'20'},
          {'hscode':'A','anbar_name':'1','tagh_name':'10'},
          {'hscode':'B','anbar_name':'3','tagh_name':None}]
    result=receipt_locations(rows)
    assert result['A']=={'anbar_names':['1','2'],'tagh_names':['10','20']}
    assert result['B']=={'anbar_names':['3'],'tagh_names':[]}


def test_missing_locations_do_not_create_placeholder_names():
    assert receipt_locations([{'hscode':'A','anbar_name':None,'tagh_name':' '}])=={'A':{'anbar_names':[],'tagh_names':[]}}
