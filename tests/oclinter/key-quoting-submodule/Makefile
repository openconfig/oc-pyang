ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ok:
	pyang --plugindir $(PLUGIN_DIR) \
		--openconfig --oc-only -p ${ROOT_DIR}/../common \
		openconfig-testcase-succeed.yang

broken:
	pyang --plugindir $(PLUGIN_DIR) \
	    --openconfig --oc-only -p ${ROOT_DIR}/../common \
			    openconfig-testcase-fail.yang
