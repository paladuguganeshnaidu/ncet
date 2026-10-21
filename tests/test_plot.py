def test_plot_page_is_public_nocache_and_uses_local_assets(client):
    response = client.get('/plot')
    assert response.status_code == 200
    assert 'noindex' in response.headers['x-robots-tag']
    assert response.headers['cache-control'] == 'no-store'
    assert 'Performance, made visible.' in response.text
    assert '/static/plot.css' in response.text
    assert '/static/plot.js' in response.text
    assert 'This is a single local sample' in response.text
    assert client.get('/static/plot.css').status_code == 200
    assert client.get('/static/plot.js').status_code == 200


def test_plot_page_keeps_theme_and_historical_metrics_labeled(client):
    html = client.get('/plot').text
    css = client.get('/static/plot.css').text
    assert 'theme-color" content="#0e2455"' in html
    assert '--navy:#0e2455' in css
    assert '--orange:#f6872a' in css
    assert 'historical source/test measurements' in html
