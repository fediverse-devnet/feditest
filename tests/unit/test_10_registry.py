"""
Test the UBOS host registry / CA
"""

import tempfile

from feditest.registry import Registry


def test_allocates_domain():
    r = Registry.create()
    assert len(r.ca.domain) > 4


def test_uses_domain():
    D = 'something.example'
    r = Registry.create( D )
    assert r.ca.domain == D


def test_root_ca():
    r = Registry.create()
    rr = r.obtain_registry_root()
    assert 'PRIVATE KEY' in rr.key
    assert 'CERTIFICATE' in rr.cert
    assert isinstance(rr.key, str)
    assert isinstance(rr.cert, str)


def test_new_hosts():
    D = 'something.example'
    r = Registry.create( D )

    h1 = r.obtain_new_hostname()
    h2 = r.obtain_new_hostname('foo')
    h3 = r.obtain_new_hostname()
    h4 = r.obtain_new_hostname('bar')

    assert h1
    assert h2
    assert h3
    assert h4
    assert h1.startswith('unnamed')
    assert h2.startswith('foo')
    assert h3.startswith('unnamed')
    assert h4.startswith('bar')
    assert h1.endswith('.' + D)
    assert h2.endswith('.' + D)
    assert h3.endswith('.' + D)
    assert h4.endswith('.' + D)


def test_new_host_and_cert():
    D = 'something.example'
    r = Registry.create( D )

    h1info = r.obtain_new_hostinfo()

    assert h1info.host.startswith('unnamed')
    assert h1info.host.endswith('.' + D)
    assert 'PRIVATE KEY' in h1info.key
    assert 'CERTIFICATE' in h1info.cert
    assert isinstance(h1info.key, str)
    assert isinstance(h1info.cert, str)


def test_save_restore():
    D = 'something.example'
    r1 = Registry.create( D )

    for i in range(5):
         r1.obtain_new_hostinfo('')

    file = tempfile.NamedTemporaryFile(delete=True).name
    r1.save(file)
    r2 = Registry.load(file)

    assert r2.ca.domain == r1.ca.domain
    assert r2.ca.key == r1.ca.key
    assert r2.ca.cert == r1.ca.cert

    assert len(r2.hosts) == len(r1.hosts)
    for host in r2.hosts:
        hostinfo1 = r1.hosts[host]
        hostinfo2 = r2.hosts[host]

        assert hostinfo1
        assert hostinfo2

        assert hostinfo2.host == hostinfo1.host
        assert hostinfo2.key == hostinfo1.key
        assert hostinfo2.cert == hostinfo1.cert

