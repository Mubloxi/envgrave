class Envgrave < Formula
  desc "Scan projects for unused, missing, duplicated, or misconfigured environment variables"
  homepage "https://github.com/Mubloxi/envgrave"
  version "1.0.0"
  license "MIT"

  if OS.mac? && Hardware::CPU.arm?
    url "https://github.com/Mubloxi/envgrave/releases/download/v1.0.0/envgrave-1.0.0-macos-arm64.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  elsif OS.mac?
    url "https://github.com/Mubloxi/envgrave/releases/download/v1.0.0/envgrave-1.0.0-macos-x64.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_SHA256"
  end

  def install
    bin.install "envgrave"
  end

  test do
    system "#{bin}/envgrave", "--version"
  end
end
