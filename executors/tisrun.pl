#!/usr/bin/env perl
# tisrun.pl -- reference VM for TIS v1, the Texectum instruction set
# emitted by perl2link.pl (Perl language in, instruction set out).
#
# The VM exists to make the instruction set checkable: it executes a
# .tis listing exactly as written, register by register, so a listing
# can be diffed against the Perl program it came from.  It is a
# semantics definition, not a speed claim -- the native path stays
# linkbin.pl (machine-code bytes) for .link inputs.
#
# Input: read_int consumes the next integer token of stdin (the
# linkbin read-int semantics); read_byte consumes one byte (-1 at
# EOF); read_eof is 1 once the token stream is exhausted.
use strict;
use warnings;

sub parse_strlit {
    my ($s) = @_;
    die "tisrun: bad string literal $s\n" unless $s =~ /\A"(.*)"\z/s;
    my $body = $1;
    $body =~ s/\\x([0-9a-f]{2})/chr hex $1/ge;
    $body =~ s/\\n/\n/g;
    $body =~ s/\\t/\t/g;
    $body =~ s/\\r/\r/g;
    $body =~ s/\\"/"/g;
    $body =~ s/\\\\/\\/g;
    return $body;
}

sub fmt_val {
    my ($v) = @_;
    return sprintf('%d', $v) if $v == int($v) && abs($v) < 9.0e15;
    return sprintf('%.15g', $v);
}

sub main {
    my ($file) = @ARGV;
    die "usage: perl tisrun.pl prog.tis\n" unless defined $file;
    open my $fh, '<', $file or die "tisrun: cannot read $file: $!\n";
    my @prog;
    my %label;
    while (my $line = <$fh>) {
        chomp $line;
        $line =~ s/\s+\z//;
        next if $line =~ /\A\s*(?:;|\z)/;
        if ($line =~ /\A(L\d+):\z/) { $label{$1} = scalar @prog; next }
        push @prog, $line;
    }
    close $fh;

    my %reg;
    my %env;
    my $inbuf = '';
    my $inloaded = 0;
    my @tokens;
    my $tokpos = 0;
    my $bytepos = 0;
    my $load_input = sub {
        return if $inloaded;
        $inloaded = 1;
        local $/;
        my $data = <STDIN>;
        $inbuf = defined $data ? $data : '';
        @tokens = $inbuf =~ /-?\d+/g;
    };

    my %fn = (
        sqrt => sub { sqrt $_[0] }, exp => sub { exp $_[0] },
        log  => sub { log $_[0] },  log2 => sub { log($_[0]) / log(2) },
        abs  => sub { abs $_[0] },  sin => sub { sin $_[0] },
        cos  => sub { cos $_[0] },  tan => sub { sin($_[0]) / cos($_[0]) },
        asin => sub { atan2($_[0], sqrt(1 - $_[0] * $_[0])) },
        acos => sub { atan2(sqrt(1 - $_[0] * $_[0]), $_[0]) },
        atan => sub { atan2($_[0], 1) },
        sinh => sub { (exp($_[0]) - exp(-$_[0])) / 2 },
        cosh => sub { (exp($_[0]) + exp(-$_[0])) / 2 },
        tanh => sub { my $e = exp(2 * $_[0]); ($e - 1) / ($e + 1) },
        floor => sub { my $v = $_[0]; $v == int($v) ? $v : ($v < 0 ? int($v) - 1 : int($v)) },
        ceil  => sub { my $v = $_[0]; $v == int($v) ? $v : ($v < 0 ? int($v) : int($v) + 1) },
        int   => sub { int $_[0] },
    );

    my $pc = 0;
    my $steps = 0;
    while ($pc >= 0 && $pc < @prog) {
        die "tisrun: step limit exceeded\n" if ++$steps > 100_000_000;
        my $ins = $prog[$pc++];
        if ($ins =~ /\A(%t\d+) = const (-?[\d.eE+-]+)\z/) {
            $reg{$1} = $2 + 0;
        } elsif ($ins =~ /\A(%t\d+) = var (\w+)\z/) {
            $reg{$1} = $env{$2} // 0;
        } elsif ($ins =~ /\A(%t\d+) = aff (%t\d+), (-?[\d.eE+-]+), (-?[\d.eE+-]+)\z/) {
            $reg{$1} = $3 * $reg{$2} + $4;
        } elsif ($ins =~ /\A(%t\d+) = (add|sub|mul|div|mod|pow|and|or) (%t\d+) ; (%t\d+)\z/) {
            my ($t, $op, $x, $s) = ($1, $2, $reg{$3}, $reg{$4});
            $reg{$t} = $op eq 'add' ? $x + $s
                     : $op eq 'sub' ? $x - $s
                     : $op eq 'mul' ? $x * $s
                     : $op eq 'div' ? $x / $s
                     : $op eq 'mod' ? $x % $s
                     : $op eq 'pow' ? $x ** $s
                     : $op eq 'and' ? (($x != 0 && $s != 0) ? 1 : 0)
                     :                (($x != 0 || $s != 0) ? 1 : 0);
        } elsif ($ins =~ /\A(%t\d+) = cmp (==|!=|<=|>=|<|>), (%t\d+) ; (%t\d+)\z/) {
            my ($t, $op, $x, $s) = ($1, $2, $reg{$3}, $reg{$4});
            $reg{$t} = $op eq '==' ? ($x == $s ? 1 : 0)
                     : $op eq '!=' ? ($x != $s ? 1 : 0)
                     : $op eq '<'  ? ($x <  $s ? 1 : 0)
                     : $op eq '<=' ? ($x <= $s ? 1 : 0)
                     : $op eq '>'  ? ($x >  $s ? 1 : 0)
                     :               ($x >= $s ? 1 : 0);
        } elsif ($ins =~ /\A(%t\d+) = fn (\w+), (%t\d+)\z/) {
            my $f = $fn{$2} or die "tisrun: unknown fn $2\n";
            $reg{$1} = $f->($reg{$3});
        } elsif ($ins =~ /\A(%t\d+) = not (%t\d+)\z/) {
            $reg{$1} = $reg{$2} == 0 ? 1 : 0;
        } elsif ($ins =~ /\A(%t\d+) = read_int\z/) {
            $load_input->();
            $reg{$1} = $tokpos < @tokens ? $tokens[$tokpos++] : 0;
        } elsif ($ins =~ /\A(%t\d+) = read_byte\z/) {
            $load_input->();
            $reg{$1} = $bytepos < length $inbuf ? ord(substr($inbuf, $bytepos++, 1)) : -1;
        } elsif ($ins =~ /\A(%t\d+) = read_eof\z/) {
            $load_input->();
            $reg{$1} = $tokpos < @tokens ? 0 : 1;
        } elsif ($ins =~ /\Astore (\w+), (%t\d+)\z/) {
            $env{$1} = $reg{$2};
        } elsif ($ins =~ /\Aprint_str (".*")\z/) {
            print parse_strlit($1);
        } elsif ($ins =~ /\Aprint_val (%t\d+)\z/) {
            print fmt_val($reg{$1});
        } elsif ($ins =~ /\Awrite_byte (%t\d+)\z/) {
            print chr($reg{$1} & 0xFF);
        } elsif ($ins =~ /\Ajmp (L\d+)\z/) {
            $pc = $label{$1};
        } elsif ($ins =~ /\Ajz (%t\d+), (L\d+)\z/) {
            $pc = $label{$2} if $reg{$1} == 0;
        } elsif ($ins =~ /\Ajnz (%t\d+), (L\d+)\z/) {
            $pc = $label{$2} if $reg{$1} != 0;
        } elsif ($ins =~ /\A(%t\d+) = exec (".*")\z/) {
            # Same semantics as the native drv_execve: on success
            # this process is replaced and never returns; on
            # failure the pole carries -errno.  envp is empty,
            # exactly as on the native path.
            my ($t, $argstr) = ($1, $2);
            my @args = map { parse_strlit('"' . $_ . '"') }
                       ($argstr =~ /"((?:[^"\\]|\\.)*)"/g);
            my $path = shift @args;   # literal 0 is the path only;
                                      # argv starts at the explicit argv0
            require IO::Handle; STDOUT->flush();
            { local %ENV = (); exec { $path } @args; }
            $reg{$t} = -($! + 0);
        } elsif ($ins eq 'halt') {
            last;
        } else {
            die "tisrun: cannot decode instruction: $ins\n";
        }
    }
}

main();
