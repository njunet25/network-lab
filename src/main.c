#include <arpa/inet.h>
#include <netinet/in.h>
#include <resolv.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>
#include <stdlib.h>

int open_icmp() {
  int raw_socket = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
  if (raw_socket < 0) {
    perror("socket: ");
    exit(1);
  }
  return raw_socket;
}

void icmp_loop(int socket) {
  char *buf = malloc(1500);
  char ip[32];
  struct sockaddr_in addr;
  unsigned int addr_len;
  while (recvfrom(socket, buf, 1500, 0, (struct sockaddr *)&addr, &addr_len)) {
    char icmp_type = buf[0+20];
    char icmp_code = buf[1+20];
    inet_ntop(AF_INET,  &addr.sin_addr,  ip,  32);

    fprintf(stderr,  "ip %s type %u code %u\n", ip, icmp_type, icmp_code);
  }
}

int main() {
  int socket = open_icmp();
  icmp_loop(socket);
  return 0;
}
