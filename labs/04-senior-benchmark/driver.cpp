// Thin scan transport: no control decisions, no sockets or real I/O.
#include "cell.hpp"
#include <iostream>
#include <sstream>
#include <string>
#include <array>
int main() {
  strucpp::CELLCONTROL cell;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::array<long long, 17> v{};
    for (auto &x : v) {
      if (!(in >> x)) { std::cerr << "invalid scan frame\n"; return 65; }
    }
    std::string extra;
    if (in >> extra) { std::cerr << "extra input fields\n"; return 65; }
    cell.STARTPB = v[0]; cell.STOPPB = v[1]; cell.RESETPB = v[2];
    cell.ESTOPOK = v[3]; cell.COMMFRESH = v[4]; cell.AUTOMODE = v[5];
    cell.DOWNSTREAMREADY = v[6]; cell.REQVALID = v[7]; cell.REQSEQ = v[8];
    cell.ACKVALID = v[9]; cell.ACKSEQ = v[10]; cell.EXTENDED = v[11];
    cell.RETRACTED = v[12]; cell.RECIPECOMMIT = v[13]; cell.RECIPEVERSION = v[14];
    cell.RECIPETIMEOUTTICKS = v[15]; cell.RECIPEDELAYTICKS = v[16];
    cell();
    std::cout
      << static_cast<int>(cell.EXTENDCMD) << ' '
      << static_cast<int>(cell.RETRACTCMD) << ' '
      << static_cast<int>(cell.FEEDPERMIT) << ' '
      << static_cast<int>(cell.BUSY) << ' '
      << static_cast<int>(cell.FAULTLATCHED) << ' '
      << static_cast<int>(cell.FAULTCODE) << ' '
      << static_cast<int>(cell.STATE) << ' '
      << static_cast<long>(cell.ACCEPTEDSEQ) << ' '
      << static_cast<long>(cell.DONESEQ) << ' '
      << static_cast<long>(cell.COMPLETEDCOUNT) << ' '
      << static_cast<long>(cell.ACTIVERECIPEVERSION) << ' '
      << static_cast<int>(cell.ACTIVETIMEOUTTICKS) << ' '
      << static_cast<int>(cell.ACTIVEDELAYTICKS) << ' '
      << static_cast<int>(cell.CYCLETIMEOUTTICKS) << ' '
      << static_cast<int>(cell.CYCLEDELAYTICKS) << ' '
      << static_cast<int>(cell.RECIPEREJECTED) << std::endl;
  }
}
