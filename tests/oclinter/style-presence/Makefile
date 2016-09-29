ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ok:
	pyang --plugindir ${ROOT_DIR}/../../../plugins \
		--openconfig --oc-only -p ${ROOT_DIR}/../common \
		${ROOT_DIR}/openconfig-testcase-succeed.yang

broken:
	pyang --plugindir ${ROOT_DIR}/../../../plugins \
	    --openconfig --oc-only -p ${ROOT_DIR}/../common \
			    ${ROOT_DIR}/openconfig-testcase-fail.yang \
						--print-error 2>&1 
