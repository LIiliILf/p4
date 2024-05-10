#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep
import grpc

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../utils/')
)
import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.error_utils import printGrpcError
from p4runtime_lib.switch import ShutdownAllSwitchConnections


# 定义进行ipv4报文转发的流表项
def writeIpForwardRules(p4info_helper, ingress_sw, egress_sw, mymatch_fields, myd):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": mymatch_fields
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": mydstaddr,
            "port": myport
        }
    )
    ingress_sw.WriteTableEntry(table_entry)


def main(p4info_file_path, bmv2_file_path):
    # Instantiate a P4Runtime helper from the p4info file
    p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)
    try:
        # s1, s2, s3, s4的配置信息
        s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s1',
            address='127.0.0.1:50051',
            device_id=0,
            proto_dump_file='logs/s1-p4runtime-requests.txt'
        )
        s2 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s2',
            address='127.0.0.1:50052',
            device_id=1,
            proto_dump_file='logs/s2-p4runtime-requests.txt'
        )
        s3 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s3',
            address='127.0.0.1:50053',
            device_id=2,
            proto_dump_file='logs/s3-p4runtime-requests.txt'
        )
        s4 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name='s3',
            address='127.0.0.1:50054',
            device_id=3,
            proto_dump_file='logs/s4-p4runtime-requests.txt'
        )

        # Send master arbitration update message to establish this controller as
        # master (required by P4Runtime before performing any other write operat
        s1.MasterArbitrationUpdate()
        s2.MasterArbitrationUpdate()
        s3.MasterArbitrationUpdate()
        s4.MasterArbitrationUpdate()

        # Install the P4 program on the switches
        s1.SetForwardingPipelineConfig(
            p4info=p4info_helper.p4info,
            bmv2_json_file_path=bmv2_file_path
        )
        print("Installed P4 Program using SetForwardingPipelineConfig on s1")

        s2.SetForwardingPipelineConfig(
            p4info=p4info_helper.p4info,
            bmv2_json_file_path=bmv2_file_path
        )
        print("Installed P4 Program using SetForwardingPipelineConfig on s2")

        s3.SetForwardingPipelineConfig(
            p4info=p4info_helper.p4info,
            bmv2_json_file_path=bmv2_file_path
        )
        print("Installed P4 Program using SetForwardingPipelineConfig on s3")

        s4.SetForwardingPipelineConfig(
            p4info=p4info_helper.p4info,
            bmv2_json_file_path=bmv2_file_path
        )
        print("Installed P4 Program using SetForwardingPipelineConfig on s4")

        # s1的流规则
        writeIpForwardRules(p4info_helper, ingress_sw=s1, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s1, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s1, egress_sw=s3, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s1, egress_sw=s4, mymatch_f)

        # s2的流规则
        writeIpForwardRules(p4info_helper, ingress_sw=s2, egress_sw=s3, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s2, egress_sw=s4, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s2, egress_sw=s2, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s2, egress_sw=s3, mymatch_f)

        # s3的流规则
        writeIpForwardRules(p4info_helper, ingress_sw=s3, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s3, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s3, egress_sw=s2, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s3, egress_sw=s1, mymatch_f)

        # s4的流规则
        writeIpForwardRules(p4info_helper, ingress_sw=s4, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s4, egress_sw=s1, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s4, egress_sw=s2, mymatch_f)
        writeIpForwardRules(p4info_helper, ingress_sw=s4, egress_sw=s2, mymatch_f)

    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        printGrpcError(e)
    ShutdownAllSwitchConnections()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='./build/link_monitor.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='./build/link_monitor.json')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found: %s\nHave you run 'make'?" % args.p4info)
        parser.exit(1)

    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found: %s\nHave you run 'make'?" % args.bmv2)
        parser.exit(1)

    main(args.p4info, args.bmv2_json)