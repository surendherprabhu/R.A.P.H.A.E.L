import pkg_resources
for pkg in pkg_resources.working_set:
    print(pkg.project_name, pkg.version)
