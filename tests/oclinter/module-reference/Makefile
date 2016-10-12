ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ok:
	pyang --plugindir $(PLUGIN_DIR) \
		--openconfig -p ${ROOT_DIR}/../common \
		${ROOT_DIR}/openconfig-testcase-succeed.yang

broken:
	pyang --plugindir $(PLUGIN_DIR) \
	    --openconfig -p ${ROOT_DIR}/../common \
			    ${ROOT_DIR}/openconfig-testcase-fail.yang \
						--print-error 2>&1
