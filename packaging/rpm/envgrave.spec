Name: envgrave
Version: 1.0.0
Release: 1%{?dist}
Summary: Scan projects for unused, missing, duplicated, or misconfigured environment variables

License: MIT
URL: https://github.com/Mubloxi/envgrave
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch
BuildRequires: python3-setuptools
Requires: python3 >= 3.10

%description
EnvGrave is a lightweight CLI tool that scans projects for unused,
missing, duplicated, or inconsistently named environment variables.

%prep
%autosetup

%build
python3 -m build --wheel --no-isolation

%install
python3 -m installer --destdir=%{buildroot} dist/*.whl

%files
%license LICENSE
%doc README.md
%{_bindir}/envgrave
%{python3_sitelib}/envgrave

%changelog
* Wed Nov 18 2026 EnvGrave <envgrave@github.com> - 1.0.0-1
- Initial release
