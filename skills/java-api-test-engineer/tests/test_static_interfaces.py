"""Source-only controller contract regressions; runnable with unittest or pytest."""
import tempfile
import unittest
from pathlib import Path

from japi.static import discover_static


class InterfaceRoutesTest(unittest.TestCase):
    def test_interface_get_post_and_parameter_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Contract.java').write_text('''package contracts;
                @RequestMapping("/orders") interface Contract {
                    @GetMapping("/{id}") String get(@PathVariable("id") long id,
                        @RequestParam("detail") boolean detail);
                    @PostMapping String create(@RequestBody Order body);
                }
                class Order { String sku; }
            ''')
            (root / 'Controller.java').write_text('''package web;
                import contracts.Contract;
                import contracts.Order;
                @RestController class Controller implements Contract {
                    public String get(long orderId, boolean verbose) { return null; }
                    public String create(Order request) { return null; }
                }
            ''')
            cat = discover_static(root)
            endpoints = {e['id']: e for e in cat['endpoints']}
            self.assertEqual(set(endpoints), {'GET /orders/{id}', 'POST /orders'})
            get = endpoints['GET /orders/{id}']
            self.assertEqual([(p['name'], p['in']) for p in get['parameters']],
                             [('id', 'path'), ('detail', 'query')])
            self.assertEqual(endpoints['POST /orders']['request_body']['content']
                             ['application/json']['schema'],
                             {'$ref': '#/components/schemas/Order'})

    def test_nested_interface_default_method_and_controller_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Routes.java').write_text('''package demo;
                interface Root {
                    @GetMapping("/items/{id}") String get(@PathVariable(name="id") long id);
                    @GetMapping("/default") default String fallback() { return "ok"; }
                    @PostMapping("/items") String create(@RequestBody String body);
                    @GetMapping("/search") String search(@RequestParam(required=false) String q);
                    @GetMapping("/search-id") String search(@RequestParam long id);
                }
                interface Child extends Root {}
                @RestController @RequestMapping("/v2")
                class Controller implements Child {
                    public String get(long renamed) { return null; }
                    @PutMapping("/custom") public String create(@RequestBody String data) { return null; }
                    public String search(String q) { return null; }
                    public String search(long id) { return null; }
                }
                @RestController @RequestMapping("/other")
                class Other extends Controller {}
            ''')
            endpoints = {e['id']: e for e in discover_static(root)['endpoints']}
            self.assertEqual(set(endpoints), {
                'GET /v2/items/{id}', 'GET /v2/default', 'PUT /v2/custom',
                'GET /v2/search', 'GET /v2/search-id',
                'GET /other/items/{id}', 'GET /other/default', 'PUT /other/custom',
                'GET /other/search', 'GET /other/search-id',
            })
            self.assertFalse(endpoints['GET /v2/search']['parameters'][0]['required'])
            self.assertEqual(endpoints['GET /v2/items/{id}']['parameters'][0]['name'], 'id')

    def test_import_resolution_and_unresolved_parent_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'First.java').write_text('''package first;
                interface Api { @GetMapping("/right") String get(); }
            ''')
            (root / 'Second.java').write_text('''package second;
                interface Api { @GetMapping("/wrong") String get(); }
            ''')
            (root / 'Controller.java').write_text('''package web;
                import first.Api;
                @RestController class Controller implements Api, Missing {
                    public String get() { return null; }
                }
                @RestController class GenericController implements GenericApi<String> {}
            ''')
            cat = discover_static(root)
            self.assertEqual([e['id'] for e in cat['endpoints']], ['GET /right'])
            self.assertTrue(any('Missing' in w for w in cat['warnings']))
            self.assertTrue(any('GenericApi<String>' in w for w in cat['warnings']))


if __name__ == '__main__':
    unittest.main()
