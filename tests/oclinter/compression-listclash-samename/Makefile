ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ok:
	pyang --plugindir $(PLUGIN_DIR) \
		--openconfig --oc-only -p ${ROOT_DIR}/../common \
		${ROOT_DIR}/openconfig-testcase-succeed.yang

broken:
	# Return an error so that we always report this broken. There is no negative
	# test in this case.
	$(error 42)
