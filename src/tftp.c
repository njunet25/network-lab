#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip_icmp.h>
#include <arpa/tftp.h>
#include <resolv.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <stdlib.h>
#include <netdb.h>
#include <errno.h>
#include "libtftp.h"


int main(int argc, char **argv) {
  if (argc != 6) {
    fprintf(stderr, "usage: %s host port remote_file local_file window_size\n", argv[0]);
    return 1;
  }

  int ret;
  struct addrinfo hints;
  struct addrinfo *result;

  memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_DGRAM;
  hints.ai_flags = 0;
  hints.ai_protocol = 0;

  ret = getaddrinfo(argv[1], argv[2], &hints, &result);

  if (ret != 0) {
    fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(ret));
    return 1;
  }

  int sfd;
  sfd = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
  if (sfd < 0) {
    perror("socket");
    return 1;
  }

  int len;
  char *buf = malloc(1024);

  short window;
  ret = sscanf(argv[5],"%d", &window);
  if (ret != 1) {
    printf("window_size should be a number.\n");
  }
  len = tftp_build_rrq(buf, 1024, argv[3], window);

  ret = sendto(sfd, buf, len, 0, result->ai_addr, result->ai_addrlen);
  if (ret < 0) {
    perror("sendto");
    return 1;
  }

  struct sockaddr addr;
  socklen_t addrlen = sizeof(struct sockaddr);
  struct timeval timeout = {
    .tv_sec = 10,
    .tv_usec = 0,
  };

  ret = setsockopt(sfd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  if (ret < 0) {
    perror("setsockopt");
    return 1;
  }

  ret = recvfrom(sfd, buf, 1024, 0, &addr, &addrlen);
  if (ret < 0) {
    perror("recvfrom");
    return 1;
  }

  char *block;

  ret = tftp_parse_oack(buf, ret, &block);
  if (ret < 0) {
    fprintf(stderr, "Remote returned error %d: %s\n", -ret, block);
    return 1;
  } else if (ret == 0) {
    fprintf(stderr, "Server rejected windowsize.");
    return 1;
  }
  window = ret;

  struct sockaddr_in *addr_in = (struct sockaddr_in *)&addr;
  char ip_addr[16];
  inet_ntop(AF_INET, &addr_in->sin_addr, ip_addr, INET_ADDRSTRLEN);
  printf("OACK from %s:%d\n", ip_addr,ntohs(addr_in->sin_port) );

  // We have learned new port of remote at this point.
  ret = connect(sfd, &addr, addrlen);
  if (ret < 0) {
    perror("connect");
    return 1;
  }

  len = tftp_build_ack(buf, 1024, 0);
  ret = send(sfd, buf, len, 0);
  if (ret < 0) {
    perror("send");
    return 1;
  }

  FILE *target = fopen(argv[4], "wb");

  timeout.tv_sec = 3;
  ret = setsockopt(sfd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  if (ret < 0) {
    perror("setsockopt");
    return 1;
  }

  tftp_loop(sfd, target, window);

  freeaddrinfo(result);
  free(buf);
  fclose(target);

  return 0;
}