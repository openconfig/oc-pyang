ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ok:
	pyang --plugindir $(PLUGIN_DIR) \
		--openconfig --oc-only -p ${ROOT_DIR}/../common \
		${ROOT_DIR}/openconfig-testcase-succeed.yang

broken:
	pyang --plugindir $(PLUGIN_DIR) \
	    --openconfig --oc-only -p ${ROOT_DIR}/../common \
			    ${ROOT_DIR}/openconfig-testcase-fail.yang \
						--print-error-code 2>&1  | grep -v OC_STYLE_AVOID_CHOICE
