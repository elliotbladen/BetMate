import copy
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd
import unittest
from ml.football.models import dixon_coles as dc
from ml.football.models.tiers import TeamState, MatchContext
from ml.football.ucl_shared_engine import price
from ml.football.ucl_researched_pricing import forecast, team_state, validate_fixture


def ratings():
    return {'teams':['h','a'],'attack':{'h':1.,'a':1.},'defence':{'h':1.,'a':1.},
            'home_adv':{'h':1.,'a':1.},'base_home_xg':1.6,'base_away_xg':1.2,
            'rho':-.13,'converged':True}


def context():
    return {'data_as_of_utc':'2026-09-07T20:00:00Z','league_results':[{'date':'2026-09-05','points':3,'source':'https://source.example/result'}],
            'rest_days':3,'availability':[{'player':'forward','position':'ST','status':'out','source':'https://source.example/news','retrieved_at_utc':'2026-09-07T19:00:00Z'},
                                       {'player':'defender','position':'CB','status':'doubtful','source':'https://source.example/news','retrieved_at_utc':'2026-09-07T19:00:00Z'}]}


class UCLResearchedPricingTests(unittest.TestCase):
    def test_rating_normalization_preserves_fitted_goal_rates(self):
        # Controlled optimum: raw attack=2, defence=1, HFA=1. Without base
        # compensation, independent normalization halves every predicted goal rate.
        data=pd.DataFrame({'Date':pd.to_datetime(['2026-01-01','2026-01-02'],utc=True),
                           'home_team':['h','a'],'away_team':['a','h'],'home_xg':[1.5,1.5],'away_xg':[1.,1.]})
        optimum=SimpleNamespace(x=np.array([np.log(2),np.log(2),0.,0.,0.,0.]),success=True,message='controlled optimum',nit=1,nfev=1)
        with patch.object(dc,'minimize',return_value=optimum):
            fixed=dc.fit(data,as_of=pd.Timestamp('2026-02-01',tz='UTC'),min_matches=1,preserve_fitted_rates=True)
            legacy=dc.fit(data,as_of=pd.Timestamp('2026-02-01',tz='UTC'),min_matches=1)
        np.testing.assert_allclose(dc.expected_goals('h','a',fixed),(3.,2.))
        np.testing.assert_allclose(dc.expected_goals('h','a',legacy),(1.5,1.))


    def test_explicit_live_context_replaces_old_archive_form(self):
        r=ratings()
        stale=pd.DataFrame({'Date':pd.to_datetime(['2020-01-01'],utc=True),'home_team':['h'],'away_team':['a'],'home_goals':[10],'away_goals':[0]})
        live=MatchContext(TeamState('h',form5_pts=7.5,rest_days=7),TeamState('a',form5_pts=7.5,rest_days=7))
        result=price('h','a',r,matches=stale,as_of='2026-09-08T00:00:00Z',context=live)
        self.assertAlmostEqual(result['lambda_home'],1.6)
        assert result['tier_audit'].t3_form_adj_h==0


    def test_absent_forward_reduces_home_win_probability(self):
        healthy=forecast('h','a',ratings(),None,MatchContext(TeamState('h'),TeamState('a')))
        injured=forecast('h','a',ratings(),None,MatchContext(TeamState('h',injuries=['ST']),TeamState('a')))
        assert injured['probabilities']['home']<healthy['probabilities']['home']
        self.assertAlmostEqual(sum(injured['probabilities'].values()),1)


    def test_doubtful_player_is_not_automatically_absent(self):
        c=context()
        assert team_state('h',c).injuries==['ST']
        assert team_state('h',c,include_doubtful=True).injuries==['ST','CB']
        assert len(c['league_results'])==1


    def test_missing_team_and_failed_fit_abstain(self):
        with self.assertRaisesRegex(ValueError,'Missing team strength'):
            forecast('h','missing',ratings(),None,None)
        r=ratings();r['converged']=False
        with self.assertRaisesRegex(ValueError,'nonconverged'):
            forecast('h','a',r,None,None)


    def test_future_results_and_post_cutoff_news_rejected(self):
        f={'kickoff_utc':'2026-09-08T19:00:00Z','home_context':context(),'away_context':context()}
        validate_fixture(f,'2026-09-08T00:00:00Z')
        future=copy.deepcopy(f);future['home_context']['league_results'][0]['date']='2026-09-09'
        with self.assertRaisesRegex(ValueError,'Future or stale'):
            validate_fixture(future,'2026-09-08T00:00:00Z')
        late=copy.deepcopy(f);late['home_context']['availability'][0]['retrieved_at_utc']='2026-09-08T01:00:00Z'
        with self.assertRaisesRegex(ValueError,'Availability observed after cutoff'):
            validate_fixture(late,'2026-09-08T00:00:00Z')


    def test_wrong_context_team_rejected(self):
        with self.assertRaisesRegex(ValueError,'context teams'):
            price('h','a',ratings(),context=MatchContext(TeamState('x'),TeamState('a')))

if __name__=="__main__": unittest.main()
