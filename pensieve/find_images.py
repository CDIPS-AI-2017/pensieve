import os
import json
import requests
from PIL import Image
import urllib
from .image import upload_image
from requests_oauthlib import OAuth1


def get_secret(service):
    """Access local store to load secrets."""
    local = os.getcwd()
    root = os.path.sep.join(local.split(os.path.sep)[:3])
    secret_pth = os.path.join(root, '.ssh', '{}.json'.format(service))
    return secret_pth


def load_secret(service):
    """Load secrets from a local store.

    Args:
        server: str defining server

    Returns:
        dict: storing key: value secrets
    """
    pth = get_secret(service)
    secret = json.load(open(pth))
    return secret

BING_API_KEY = load_secret('bing')
NP_API_KEY, NP_API_SECRET = load_secret('noun_project')

def search_bing_for_image(query):
    """
    Perform a Bing image search.

    Args:
        query: Image search query

    Returns:
        results: List of urls from results
    """
    search_params = {'q': query,
                     'mkt': 'en-us',
                     'safeSearch': 'strict'}
    auth = {'Ocp-Apim-Subscription-Key': BING_API_KEY}
    url = 'https://api.cognitive.microsoft.com/bing/v5.0/images/search'
    r = requests.get(url, params=search_params, headers=auth)
    results = r.json()['value']
    urls = [result['contentUrl'] for result in results]
    return urls

def search_np_for_image(query):
    """
    Perform a Noun Project image search.

    Args:
        query: Image search query

    Returns:
        results: List of image result JSON dicts
    """
    auth = OAuth1(NP_API_KEY, NP_API_SECRET)
    endpoint = 'http://api.thenounproject.com/icons/{}'.format(query)
    params = {'limit_to_public_domain': 1,
              'limit': 5}
    response = requests.get(endpoint, params=params, auth=auth)
    urls = [icon['preview_url'] for icon in response.json()['icons']]
    return urls

def store_best(search_results, n=1):
    """
    Store the top n results from a search in S3 bucket.

    Args:
        search_results: list of search result JSON dicts
        n: number of results to store

    Returns:
        urls: urls of images
        success: list of S3 upload success states
        full_key_names: list of uuids to store in imageURL
    """
    urls, success, full_key_names = [], [], []
    for i, result in enumerate(search_results):
        if i >= n:
            break
        urls.append(result['contentUrl'])
    for url in urls:
        s, fkn = upload_image(url)
        success.append(s)
        full_key_names.append(fkn)
    return urls, success, full_key_names


def view(urls):
    """
    View the images at url

    Args:
        urls: list of image urls to view

    Returns:
        None
    """
    for i, url in enumerate(urls):
        resp = requests.get(url)
        dat = urllib.request.urlopen(resp.url)
        img = Image.open(dat)
        img.show()

if __name__ == '__main__':
    # try:
    #     with open('example_bing_result.pkl', 'rb') as f:
    #         results_json = pickle.load(f)
    # except IOError:
    #     results_json = search_bing_for_image('wand')
    #     with open('example_bing_result.pkl', 'wb') as f:
    #         pickle.dump(results_json, f)

    results_json = search_bing_for_image('Harry Potter')
    results_list = results_json
    best_urls = [r['contentUrl'] for r in results_list][:3]
    view(best_urls)
