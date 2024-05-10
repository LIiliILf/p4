/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;      // 用于表示数据包的类型是 IPv4 类型
const bit<16> TYPE_SRCROUTING = 0x1234;// 用于表示数据包的类型是源路由类型
#define MAX_HOPS 9                      // 用于指定数据包中最大的跳数，即源路由中包含的最大中间节点数

/*************************************************************************
*********************** H E A D E R S ***********************************
*************************************************************************/

typedef bit<9> egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16> etherType;
}

header srcRoute_t {
    bit<1> bos;     // 用于表示起始点/终点标记等信息
    bit<15> port;   // 用于表示网络中的一个端口号
}

header ipv4_t {
    bit<4> version;
    bit<4> ihl;
    bit<8> diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3> flags;
    bit<13> fragOffset;
    bit<8> ttl;
    bit<8> protocol;
    bit<16> hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

struct metadata {
    /* empty */
}

struct headers {
    ethernet_t ethernet;
    srcRoute_t[MAX_HOPS] srcRoutes;
    ipv4_t ipv4;
}

/*************************************************************************
*********************** P A R S E R ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_SRCROUTING: parse_srcRouting;  // 判断以太网帧的类型是否为 TYPE_SRCROUT
            default: accept;
        }
    }

    state parse_srcRouting {
        packet.extract(hdr.srcRoutes.next);    // 用于从数据包中提取源路由信息
        transition select(hdr.srcRoutes.last.bos) {
            1: parse_ipv4;
            default: parse_srcRouting;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition accept;
    }
}

/*************************************************************************
************ C H E C K S U M V E R I F I C A T I O N *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/*************************************************************************
************** I N G R E S S P R O C E S S I N G *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop();
    }

    action srcRoute_nhop() {
        standard_metadata.egress_spec = (bit<9>) hdr.srcRoutes[0].port; // 从数据包的
        hdr.srcRoutes.pop_front(1);                                     // 删除已经处理的下一个跳信息（pop_front 操作）
    }

    action srcRoute_finish() {
        hdr.ethernet.etherType = TYPE_IPV4; // 在源路由处理完成之后，数据包需要按照 IPv4
    }

    apply {
        if (hdr.srcRoutes[0].isValid()) {
            if (hdr.srcRoutes[0].bos == 1) {    // 判断源路由头部中的第一个下一跳是否为最后一
                srcRoute_finish();
            }
            srcRoute_nhop();
            if (hdr.ipv4.isValid()) {
                ipv4_lpm.apply();
            }
        } else {
            drop();
        }
    }
}

/*************************************************************************
**************** E G R E S S P R O C E S S I N G *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

/*************************************************************************
************* C H E C K S U M C O M P U T A T I O N **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/*************************************************************************
*********************** D E P A R S E R *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.srcRoutes);
        packet.emit(hdr.ipv4);
    }
}

/*************************************************************************
*********************** S W I T C H *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;