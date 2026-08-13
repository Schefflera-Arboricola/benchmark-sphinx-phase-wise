# [WIP] benchmark-sphinx-phase-wise

To benchmark the Sphinx docs build process handler-wise (broken down by [event](https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html) and by extension). Right now, benchmarks are computed by wrapping each handler function registered against an event (each `EventListener` in `app.events.listeners`), rather than the event as a whole.

## Demo output

For Matplotlib docs build:

```bash
Event                                   Calls       Total(s)        Avg(ms)    %Build
-------------------------------------------------------------------------------------
config-inited                               1     407.897459     407897.459    51.76%
doctree-resolved                         2081     159.895919         76.836    20.29%
source-read                              2081     118.485265         56.937    15.03%
object-description-transform             7034      71.411225         10.152     9.06%
doctree-read                             2081      19.743725          9.488     2.51%
env-purge-doc                            2081       4.523341          2.174     0.57%
write-started                               1       1.744397       1744.397     0.22%
builder-inited                              1       1.361653       1361.653     0.17%
include-read                               50       1.286405         25.728     0.16%
warn-missing-reference                    141       1.183458          8.393     0.15%
env-updated                                 1       0.538349        538.349     0.07%
env-before-read-docs                        1       0.000224          0.224     0.00%
env-check-consistency                       1       0.000117          0.117     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

For NumPy docs build:

```bash
Event                                   Calls       Total(s)        Avg(ms)    %Build
-------------------------------------------------------------------------------------
doctree-resolved                         2673     151.714524         56.758    50.05%
source-read                              2673     112.351479         42.032    37.06%
object-description-transform             3480      16.495565          4.740     5.44%
config-inited                               1       9.698906       9698.906     3.20%
env-purge-doc                            2673       5.636594          2.109     1.86%
doctree-read                             2673       4.485057          1.678     1.48%
include-read                               25       1.214643         48.586     0.40%
builder-inited                              1       0.841800        841.800     0.28%
env-updated                                 1       0.504075        504.075     0.17%
write-started                               1       0.210907        210.907     0.07%
env-before-read-docs                        1       0.000199          0.199     0.00%
env-check-consistency                       1       0.000153          0.153     0.00%
build-finished                              1       0.000000          0.000     0.00%
```

For NetworkX docs build:

```bash
sphinx_benchmarks.json written

========================================================================================================================================================
builder-inited  —  96.041204s total  (84.27% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  generate_gallery_rst                              extension           sphinx_gallery.gen_gallery                       1      93.078481      93078.481
  load_mappings                                     sphinx-internal     -                                                1       1.770456       1770.456
  process_generate_options                          sphinx-internal     -                                                1       1.190647       1190.647
  wrap_all_listeners                                extension           benchmark_sphinx_phase_wise                      1       0.000670          0.670
  create_mystnb_config                              extension           myst_nb                                          1       0.000477          0.477
  create_myst_config                                unknown             -                                                1       0.000413          0.413
  update_gallery_conf_builder_inited                extension           sphinx_gallery.gen_gallery                       1       0.000037          0.037
  init_filename_registry                            extension           matplotlib.sphinxext.plot_directive              1       0.000009          0.009
  override_mathjax                                  unknown             -                                                1       0.000005          0.005
  validate_math_renderer                            sphinx-internal     -                                                1       0.000004          0.004
  _init_stuff                                       sphinx-internal     -                                                1       0.000003          0.003
  validate_config_values                            sphinx-internal     -                                                1       0.000002          0.002
  install_packages_for_ja                           sphinx-internal     -                                                1       0.000001          0.001

========================================================================================================================================================
autodoc-process-docstring  —  7.246518s total  (6.36% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  mangle_docstrings                                 extension           numpydoc                                      2843       6.915641          2.433
  touch_empty_backreferences                        extension           sphinx_gallery.gen_gallery                    2843       0.256492          0.090
  mathdollar_docstrings                             extension           texext                                        2843       0.071689          0.025
  write_api_entries                                 extension           sphinx_gallery.gen_gallery                    2843       0.002697          0.001

========================================================================================================================================================
autodoc-process-signature  —  5.057733s total  (4.44% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  mangle_signature                                  extension           numpydoc                                      2843       5.057733          1.779

========================================================================================================================================================
html-page-context  —  2.951201s total  (2.59% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  update_and_remove_templates                       extension           pydata_sphinx_theme                           1824       1.556136          0.853
  set_secondary_sidebar_items                       extension           pydata_sphinx_theme                           1824       1.277741          0.701
  add_toctree_functions                             extension           pydata_sphinx_theme                           1824       0.061702          0.034
  setup_resource_paths                              sphinx-internal     -                                             1824       0.016670          0.009
  add_per_page_html_resources                       extension           myst_nb                                       1824       0.009995          0.005
  install_mathjax                                   sphinx-internal     -                                             1824       0.009787          0.005
  setup_template_link_getters                       extension           sphinx_gallery.gen_gallery                    1824       0.005691          0.003
  setup_logo_path                                   extension           pydata_sphinx_theme                           1824       0.005466          0.003
  setup_edit_url                                    extension           pydata_sphinx_theme                           1824       0.003614          0.002
  update_context                                    extension           alabaster                                     1824       0.002576          0.001
  _fix_canonical_url                                extension           pydata_sphinx_theme                           1824       0.001823          0.001

========================================================================================================================================================
doctree-read  —  1.430412s total  (1.26% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  TocTreeCollector.process_doc                      sphinx-internal     -                                             1561       0.412298          0.264
  DependenciesCollector.process_doc                 sphinx-internal     -                                             1561       0.318068          0.204
  doctree_read                                      sphinx-internal     -                                             1561       0.190056          0.122
  ImageCollector.process_doc                        sphinx-internal     -                                             1561       0.182810          0.117
  DownloadFileCollector.process_doc                 sphinx-internal     -                                             1561       0.143228          0.092
  relabel_references                                extension           numpydoc                                      1561       0.116653          0.075
  TitleCollector.process_doc                        sphinx-internal     -                                             1561       0.052368          0.034
  MetadataCollector.process_doc                     sphinx-internal     -                                             1561       0.007823          0.005
  mark_plot_labels                                  extension           matplotlib.sphinxext.plot_directive           1561       0.004537          0.003
  _FilenameCollector.process_doc                    extension           matplotlib.sphinxext.plot_directive           1561       0.001483          0.001
  NbMetadataCollector.process_doc                   extension           myst_nb                                       1561       0.001087          0.001

========================================================================================================================================================
env-purge-doc  —  0.491128s total  (0.43% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  env_purge_doc                                     sphinx-internal     -                                             1561       0.221046          0.142
  TocTreeCollector.clear_doc                        sphinx-internal     -                                             1561       0.149137          0.096
  DownloadFileCollector.clear_doc                   sphinx-internal     -                                             1561       0.081025          0.052
  ImageCollector.clear_doc                          sphinx-internal     -                                             1561       0.030848          0.020
  DependenciesCollector.clear_doc                   sphinx-internal     -                                             1561       0.002403          0.002
  NbMetadataCollector.clear_doc                     extension           myst_nb                                       1561       0.002119          0.001
  TitleCollector.clear_doc                          sphinx-internal     -                                             1561       0.001735          0.001
  _FilenameCollector.clear_doc                      extension           matplotlib.sphinxext.plot_directive           1561       0.001502          0.001
  MetadataCollector.clear_doc                       sphinx-internal     -                                             1561       0.001313          0.001

========================================================================================================================================================
build-finished  —  0.402307s total  (0.35% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  embed_code_links                                  extension           sphinx_gallery.gen_gallery                       1       0.366879        366.879
  overwrite_pygments_css                            extension           pydata_sphinx_theme                              1       0.032602         32.602
  add_global_html_resources                         extension           myst_nb                                          1       0.001178          1.178
  _copy_css_file                                    extension           matplotlib.sphinxext.plot_directive              1       0.000998          0.998
  clean_api_usage_files                             extension           sphinx_gallery.gen_gallery                       1       0.000454          0.454
  summarize_failing_examples                        extension           sphinx_gallery.gen_gallery                       1       0.000110          0.110
  create_jupyterlite_contents                       extension           sphinx_gallery.gen_gallery                       1       0.000046          0.046
  copy_binder_files                                 extension           sphinx_gallery.gen_gallery                       1       0.000022          0.022
  copy_logo_images                                  extension           pydata_sphinx_theme                              1       0.000017          0.017

========================================================================================================================================================
doctree-resolved  —  0.223805s total  (0.20% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  clean_backrefs                                    extension           numpydoc                                      1561       0.223805          0.143

========================================================================================================================================================
missing-reference  —  0.104094s total  (0.09% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  missing_reference                                 sphinx-internal     -                                             4857       0.092070          0.019
  builtin_resolver                                  sphinx-internal     -                                             4857       0.012023          0.002

========================================================================================================================================================
object-description-transform  —  0.016743s total  (0.01% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  filter_meta_fields                                sphinx-internal     -                                             1317       0.014949          0.011
  _merge_typehints                                  sphinx-internal     -                                             1317       0.001794          0.001

========================================================================================================================================================
source-read  —  0.006574s total  (0.01% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  install_dispatcher                                sphinx-internal     -                                             1561       0.004812          0.003
  write_api_entry_usage                             extension           sphinx_gallery.gen_gallery                    1561       0.001762          0.001

========================================================================================================================================================
warn-missing-reference  —  0.000052s total  (0.00% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  warn_missing_reference                            sphinx-internal     -                                                1       0.000052          0.052

========================================================================================================================================================
env-get-updated  —  0.000030s total  (0.00% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  TocTreeCollector.get_updated_docs                 sphinx-internal     -                                                1       0.000024          0.024
  EnvironmentCollector.get_updated_docs             sphinx-internal     -                                                7       0.000006          0.001

========================================================================================================================================================
env-updated  —  0.000018s total  (0.00% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  update_exec_tables                                extension           myst_nb                                          1       0.000018          0.018

========================================================================================================================================================
html-collect-pages  —  0.000011s total  (0.00% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  collect_pages                                     sphinx-internal     -                                                1       0.000011          0.011

========================================================================================================================================================
env-get-outdated  —  0.000008s total  (0.00% of build)
========================================================================================================================================================
  Handler                                           Kind                Ext                                          Calls       Total(s)        Avg(ms)
--------------------------------------------------------------------------------------------------------------------------------------------------------
  EnvironmentCollector.get_outdated_docs            sphinx-internal     -                                                7       0.000003          0.000
  check_master_doc                                  sphinx-internal     -                                                1       0.000003          0.003
  NbMetadataCollector.get_outdated_docs             extension           myst_nb                                          1       0.000001          0.001

build succeeded, 5 warnings.
```

For CPython docs build:

```bash
ToDo
```

---

## How to use it?

In your sphinx's `conf.py` add the following:

```python
extensions = [
    "benchmark_sphinx_phase_wise",
]
```

---

Just for reference: 

- benchmarks for phase-wise benchmarking for matplotlib:

```bash
==================================================
Sphinx phase-wise benchmarks
==================================================

Initialization :  452.402 s
Reading        :  207.971 s
Consistency    :    0.699 s
Pre-writing    :    0.000 s
Resolving      :  180.908 s
Writing        :    7.531 s

--------------------------------------------------
Total          :  849.511 s
```

- benchmarks from the previous "time-stampped logging messages" approach for matplotlib:

```bash
=== Main Phase Benchmarks ===

Initialization        443.825 s
Reading               233.482 s
Consistency             0.051 s
Resolving               3.702 s
Writing               182.212 s
```

---


Thank you for stopping by :)
